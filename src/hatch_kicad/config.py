# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Any

from hatchling.builders.config import BuilderConfig


class KicadBuilderConfig(BuilderConfig):
    _BASE = "tool.hatch.build.targets.kicad-package"

    def required_str(self, name: str) -> str:
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
            raise TypeError(msg)
        if isinstance(value, list):
            value = "".join(value)
        return value

    @property
    def name(self) -> str:
        """
        The human-readable name of the package
        """
        return self.required_str("name")

    @property
    def description(self) -> str:
        """
        A short free-form description of the package that will be shown
        in the PCM alongside the package name.
        May contain a maximum of 150 characters.
        """
        return self.required_str("description")

    @property
    def description_full(self) -> str:
        """
        A long free-form description of the package that will be shown
        in the PCM when the package is selected by the user.
        May be a string or list of strings with included line breaks.
        """
        return self.required_str("description_full")

    @property
    def identifier(self) -> str:
        """
        The unique identifier for the package.
        May contain only alphanumeric characters and the dash (-) symbol.
        Must be between 2 and 50 characters in length.
        Must start with a latin character and end with a latin character or a numeral.
        """
        return self.required_str("identifier")

    @property
    def type(self) -> str:
        return "plugin"

    def get_person(self, name: str) -> dict | None:
        if name in self.target_config:
            person = self.target_config[name]
            if not isinstance(person, dict):
                msg = f"Field `{self._BASE}.{name}` must be a dictionary"
                raise TypeError(msg)
            if "name" not in person:
                msg = f"Field `{self._BASE}.{name}` must have `name` property"
                raise TypeError(msg)
            name = person["name"]
            contact = person
            del contact["name"]
            return {"name": name, "contact": contact}
        return None

    @property
    def author(self) -> dict:
        """
        Object containing one mandatory field, `name`, containing the name
        of the package creator.
        An optional `contact` field may be present,
        containing free-form fields with contact information.
        """
        author = self.get_person("author")
        if not author:
            authors = self.builder.metadata.core.authors
            if authors and "name" in authors[0]:
                author = {
                    "name": authors[0]["name"],
                }
                if "email" in authors[0]:
                    author["contact"] = {"email": authors[0]["email"]}
                else:
                    author["contact"] = {}
            else:
                msg = (
                    f"Field `{self._BASE}.author` not found, "
                    "failed to get author from `project.authors` value"
                )
                raise TypeError(msg)
        return author

    @property
    def maintainer(self) -> dict:
        """
        Semantics same as `author`, but containing information
        about the maintainer of the package
        """
        maintainer = self.get_person("maintainer")
        if not maintainer:
            maintainers = self.builder.metadata.core.maintainers
            if maintainers and "name" in maintainers[0]:
                maintainer = {
                    "name": maintainers[0]["name"],
                    "contact": {"email": maintainers[0].get("email", "-")},
                }
            else:
                maintainer = {}
        return maintainer

    @property
    def license(self):
        # if `self.config` does not contain `license`,
        # try to deduce it from project settings
        if "license" in self.target_config:
            lic = self.required_str("license")
        elif not (lic := self.builder.metadata.core.license):
            msg = (
                "Field `tool.hatch.build.targets.kicad-package.license` not found, "
                "failed to deduce license from `project.license` value.\n"
                'Define `license = {text = "<value>"} in `project` or '
                '`license = "<value>" in `tool.hatch.build.targets.kicad-package'
            )
            raise TypeError(msg)
        return lic

    @property
    def resources(self):
        if "resources" in self.target_config:
            resources = self.target_config["resources"]
            if not isinstance(resources, dict):
                msg = f"Field `{self._BASE}.resources` must be a dictionary"
                raise TypeError(msg)
        else:
            # `resources` are not mandatory so if can't be found nothing happens
            resources = self.builder.metadata.core.urls
        return resources

    @property
    def keep_on_update(self):
        """
        Not supported yet
        """
        return None

    @property
    def status(self):
        """
        A string containing one of the following:
        stable: This package is stable for general use.
        testing: This package is in a testing phase,
                 users should be cautious and report issues.
        development: This package is in a development phase
                     and should not be expected to work fully.
        deprecated: This package is no longer maintained.
        """
        return self.required_str("status")

    @property
    def kicad_version(self):
        """
        The minimum required KiCad version for this package
        """
        return self.required_str("kicad_version")

    @property
    def kicad_version_max(self):
        """
        The latest KiCad version this package is compatible with
        """
        if "kicad_version_max" in self.target_config:
            kicad_version_max = self.required_str("kicad_version_max")
        else:
            kicad_version_max = None
        return kicad_version_max

    @property
    def tags(self) -> list[str] | None:
        """
        The list of tags
        """
        if "tags" in self.target_config:
            tags = self.target_config["tags"]
            if not (
                isinstance(tags, list)
                and len(tags)
                and all(isinstance(item, str) for item in tags)
            ):
                msg = f"Field `{self._BASE}.tags` must be list of strings"
                raise TypeError(msg)
            return tags
        return None

    def get_metadata(self) -> dict[str, Any]:
        metadata = {
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
                    "version": self.builder.metadata.version,
                    "status": self.status,
                    "kicad_version": self.kicad_version,
                    "kicad_version_max": self.kicad_version_max,
                }
            ],
        }
        # remove empty optional fields
        for name in ["maintainer", "resources", "tags"]:
            if not metadata[name]:
                del metadata[name]
        if not metadata["versions"][0]["kicad_version_max"]:
            del metadata["versions"][0]["kicad_version_max"]

        return metadata
