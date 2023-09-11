# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TypedDict

from hatchling.builders.config import BuilderConfig
from hatchling.utils.context import Context
from packaging.version import parse

from hatch_kicad.licenses.supported import LICENSES


class Person(TypedDict):
    name: str
    contact: dict[str, str]


class KicadBuilderConfig(BuilderConfig):
    _BASE = "tool.hatch.build.targets.kicad-package"
    _CONTACT_KEY_REGEX = r"^[a-zA-Z][-a-zA-Z0-9 ]{0,48}[a-zA-Z0-9]$"
    # KiCad allow only this simplistic version scheme:
    # (taken from https://go.kicad.org/pcm/schemas/v1)
    _VERSION_REGEX = r"^\d{1,4}(\.\d{1,4}(\.\d{1,6})?)?$"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

        self.__context: Context | None = None
        self.__zip_name: str | None = None
        self.__name: str | None = None
        self.__description: str | None = None
        self.__description_full: str | None = None
        self.__identifier: str | None = None
        self.__author: Person | None = None
        self.__maintainer: Person | None = None
        self.__license: str | None = None
        self.__resources: dict[Any, Any] | None = None
        self.__status: str | None = None
        self.__kicad_version: str | None = None
        self.__kicad_version_max: str | None = None
        self.__tags: list[str] | None = None
        self.__icon: Path | None = None
        self.__version: str | None = None
        self.__download_url: str | None = None

    @property
    def context(self) -> Context:
        if self.__context is None:
            self.__context = Context(self.root)
        return self.__context

    @property
    def zip_name(self) -> str:
        if self.__zip_name is None:
            project_name = self.builder.normalize_file_name_component(
                self.builder.metadata.core.raw_name
            )
            self.__zip_name = f"{project_name}-{self.builder.metadata.version}.zip"
        return self.__zip_name

    def required_str(self, name: str, max_length: int = -1) -> str:
        if name in self.target_config:
            value = self.target_config[name]
            if not isinstance(value, str) and not (
                isinstance(value, list)
                and len(value)
                and all(isinstance(item, str) for item in value)
            ):
                msg = f"Field `{self._BASE}.{name}` must be a string or list of strings"
                raise TypeError(msg)
        else:
            msg = f"Field `{self._BASE}.{name}` not found"
            raise ValueError(msg)
        if isinstance(value, list):
            value = "".join(value)
        if max_length > 0:
            value_length = len(value)
            if value_length > max_length:
                msg = (
                    f"Field `{self._BASE}.{name}` too long, "
                    f"can be {max_length} character long, got {value_length}"
                )
                raise ValueError(msg)
        return value

    @property
    def name(self) -> str:
        """
        The human-readable name of the package
        """
        if not self.__name:
            self.__name = self.required_str("name", max_length=200)
        return self.__name

    @property
    def description(self) -> str:
        """
        A short free-form description of the package that will be shown
        in the PCM alongside the package name.
        May contain a maximum of 150 characters.
        """
        if not self.__description:
            self.__description = self.required_str("description", max_length=500)
        return self.__description

    @property
    def description_full(self) -> str:
        """
        A long free-form description of the package that will be shown
        in the PCM when the package is selected by the user.
        May be a string or list of strings with included line breaks.
        """
        if not self.__description_full:
            self.__description_full = self.required_str(
                "description_full", max_length=5000
            )
        return self.__description_full

    @property
    def identifier(self) -> str:
        """
        The unique identifier for the package.
        May contain only alphanumeric characters and the dash (-) symbol.
        Must be between 2 and 50 characters in length.
        Must start with a latin character and end with a latin character or a numeral.
        """
        if not self.__identifier:
            self.__identifier = self.required_str("identifier")
        return self.__identifier

    @property
    def type(self) -> str:
        return "plugin"

    def validate_person(self, person: Person, field_name: str) -> None:
        name_length = len(person["name"])
        max_length = 500
        if name_length > max_length:
            msg = (
                f"Field `{field_name}` `name` property too long, "
                f"can be {max_length} character long, got {name_length}"
            )
            raise ValueError(msg)

        contact = person["contact"]
        for k, v in contact.items():
            contact_value_length = len(v)
            if contact_value_length > max_length:
                msg = (
                    f"Field `{field_name}` `{k}` property too long, "
                    f"can be {max_length} character long, got {contact_value_length}"
                )
                raise ValueError(msg)
            if not re.match(self._CONTACT_KEY_REGEX, k):
                msg = (
                    f"Field `{field_name}` `{k}` property has "
                    "invalid format, must match following regular "
                    f"expression: `{self._CONTACT_KEY_REGEX}`"
                )
                raise ValueError(msg)

    def get_person(self, name: str) -> Person | None:
        if name in self.target_config:
            person = self.target_config[name]
            if not isinstance(person, dict):
                msg = f"Field `{self._BASE}.{name}` must be a dictionary"
                raise TypeError(msg)
            if "name" not in person:
                msg = f"Field `{self._BASE}.{name}` must have `name` property"
                raise TypeError(msg)
            contact = {k: v for k, v in person.items() if k != "name"}
            person = Person(name=person["name"], contact=contact)
            self.validate_person(person, f"{self._BASE}.{name}")
            return person
        return None

    @property
    def author(self) -> Person:
        """
        Object containing one mandatory field, `name`, containing the name
        of the package creator.
        An optional `contact` field may be present,
        containing free-form fields with contact information.
        """
        if not self.__author:
            author: Person | None = self.get_person("author")
            if not author:
                authors: list[Any] = self.builder.metadata.core.authors
                if authors and "name" in authors[0]:
                    name = authors[0]["name"]
                    contact = {}
                    if email := authors[0].get("email", {}):
                        contact = {"email": email}
                    author = Person(name=name, contact=contact)
                    self.validate_person(author, "project.authors[0]")
                else:
                    msg = (
                        f"Field `{self._BASE}.author` not found, "
                        "failed to get author from `project.authors` value"
                    )
                    raise ValueError(msg)
            self.__author = author
        return self.__author

    @property
    def maintainer(self) -> Person | None:
        """
        Semantics same as `author`, but containing information
        about the maintainer of the package
        """
        if not self.__maintainer:
            maintainer: Person | None = self.get_person("maintainer")
            if not maintainer:
                maintainers: list[Any] = self.builder.metadata.core.maintainers
                if maintainers and "name" in maintainers[0]:
                    name = maintainers[0]["name"]
                    contact = {}
                    if email := maintainers[0].get("email", {}):
                        contact = {"email": email}
                    maintainer = Person(name=name, contact=contact)
                    try:
                        self.validate_person(maintainer, "project.maintainers[0]")
                    except Exception:
                        # if fallback maintainer does not meet schema,
                        # ignore it since is not required option
                        maintainer = None
                else:
                    maintainer = None
            self.__maintainer = maintainer
        return self.__maintainer

    @property
    def license(self) -> str:
        if not self.__license:
            # if `self.config` does not contain `license`,
            # try to deduce it from project settings
            if "license" in self.target_config:
                _license = self.required_str("license")
            elif not (_license := self.builder.metadata.core.license):
                msg = (
                    "Field `tool.hatch.build.targets.kicad-package.license` not found, "
                    "failed to deduce license from `project.license` value.\n"
                    'Define `license = {text = "<value>"} in `project` or '
                    '`license = "<value>" in `tool.hatch.build.targets.kicad-package'
                )
                raise ValueError(msg)

            if _license not in LICENSES:
                repo = "https://github.com/adamws/hatch-kicad/"
                url = f"{repo}blob/master/src/hatch_kicad/licenses/supported.py"
                msg = (
                    f"Invalid license value: `{_license}`\n"
                    f"For the list of the supported licenses visit: {url}"
                )
                raise ValueError(msg)
            self.__license = _license
        return self.__license

    @property
    def resources(self) -> dict[Any, Any]:
        if not self.__resources:
            if "resources" in self.target_config:
                resources: dict[Any, Any] = self.target_config["resources"]
                if not isinstance(resources, dict):
                    msg = f"Field `{self._BASE}.resources` must be a dictionary"
                    raise TypeError(msg)
            else:
                # `resources` are not mandatory so if can't be found nothing happens
                resources = self.builder.metadata.core.urls
            self.__resources = resources
        return self.__resources

    @property
    def keep_on_update(self):
        """
        Not supported yet
        """
        return None

    @property
    def status(self) -> str:
        """
        A string containing one of the following:
        stable: This package is stable for general use.
        testing: This package is in a testing phase,
                 users should be cautious and report issues.
        development: This package is in a development phase
                     and should not be expected to work fully.
        deprecated: This package is no longer maintained.
        """
        if not self.__status:
            status = self.context.format(self.required_str("status"))
            if status not in ["stable", "testing", "development", "deprecated"]:
                msg = (
                    f"Invalid `{self._BASE}.status` value.\n"
                    "`status` must be one of: `stable`, `testing`, "
                    "`development` or `deprecated`."
                )
                raise ValueError(msg)
            self.__status = status
        return self.__status

    @property
    def kicad_version(self) -> str:
        """
        The minimum required KiCad version for this package
        """
        if not self.__kicad_version:
            kicad_version = self.required_str("kicad_version")
            if not re.match(self._VERSION_REGEX, kicad_version):
                msg = (
                    f"Field `{self._BASE}.kicad_version` has "
                    "invalid format, must match following regular "
                    f"expression: `{self._VERSION_REGEX}`"
                )
                raise ValueError(msg)
            self.__kicad_version = kicad_version
        return self.__kicad_version

    @property
    def kicad_version_max(self) -> str:
        """
        The latest KiCad version this package is compatible with
        """
        if not self.__kicad_version_max:
            if "kicad_version_max" in self.target_config:
                kicad_version_max = self.required_str("kicad_version_max")
                if not re.match(self._VERSION_REGEX, kicad_version_max):
                    msg = (
                        f"Field `{self._BASE}.kicad_version_max` has "
                        "invalid format, must match following regular "
                        f"expression: `{self._VERSION_REGEX}`"
                    )
                    raise ValueError(msg)
            else:
                kicad_version_max = ""
            self.__kicad_version_max = kicad_version_max
        return self.__kicad_version_max

    @property
    def tags(self) -> list[str]:
        """
        The list of tags
        """
        if not self.__tags:
            if "tags" in self.target_config:
                tags: list[str] = self.target_config["tags"]
                if not (
                    isinstance(tags, list)
                    and len(tags)
                    and all(isinstance(item, str) for item in tags)
                ):
                    msg = f"Field `{self._BASE}.tags` must be list of strings"
                    raise TypeError(msg)
            else:
                tags = []
            self.__tags = tags
        return self.__tags

    @property
    def icon(self) -> Path:
        if not self.__icon:
            if "icon" in self.target_config:
                icon = self.target_config["icon"]
                if not isinstance(icon, str):
                    msg = f"Field `{self._BASE}.icon` must be a string"
                    raise TypeError(msg)
                if not Path(icon).is_file():
                    msg = f"Field `{self._BASE}.icon` must point to a file"
                    raise ValueError(msg)
            else:
                msg = f"Field `{self._BASE}.icon` not found"
                raise ValueError(msg)
            self.__icon = Path(icon)
        return self.__icon

    @property
    def version(self) -> str:
        if not self.__version:
            version = self.builder.metadata.version
            if not re.match(self._VERSION_REGEX, version):
                version = str(parse(version).base_version)
            self.__version = version
        return self.__version

    @property
    def download_url(self) -> str:
        if not self.__download_url:
            if "download_url" in self.target_config:
                url = self.target_config["download_url"]
                if not isinstance(url, str):
                    msg = f"Field `{self._BASE}.download_url` must be a string"
                    raise TypeError(msg)

                def _format(value: str) -> str:
                    return self.context.format(
                        value,
                        version=self.version,
                        status=self.status,
                        zip_name=self.zip_name,
                    )

                # run two passes of `_format` in case environment variable value
                # uses supported fields, for example:
                # ENV = "http://foo.bar/{status}/plugin.zip"
                # download_url = "{env:ENV:http://bar.baz/development/{zip_name}}"
                url = _format(_format(url))
            else:
                url = ""
            self.__download_url = url
        return self.__download_url

    def get_metadata(self) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "$schema": "https://go.kicad.org/pcm/schemas/v1",
            "name": self.name,
            "description": self.description,
            "description_full": self.description_full,
            "identifier": self.identifier,
            "type": self.type,
            "author": self.author,
            "maintainer": self.maintainer,
            "license": self.license,
            "resources": self.resources,
            "tags": self.tags,
            "versions": [
                {
                    "version": self.version,
                    "status": self.status,
                    "kicad_version": self.kicad_version,
                    "kicad_version_max": self.kicad_version_max,
                }
            ],
        }
        # remove empty optional fields
        for name in ["maintainer", "tags"]:
            if not metadata[name]:
                del metadata[name]
        if not metadata["versions"][0]["kicad_version_max"]:
            del metadata["versions"][0]["kicad_version_max"]

        return metadata
