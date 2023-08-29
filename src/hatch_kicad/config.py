# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Optional

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

    def optional_str(self, name: str) -> Optional[str]:
        try:
            return self.required_str(name)
        except Exception:
            return None

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

    def get_person(self, name: str) -> Optional[dict]:
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
    def author(self) -> Optional[dict]:
        """
        Object containing one mandatory field, `name`, containing the name
        of the package creator.
        An optional `contact` field may be present,
        containing free-form fields with contact information.
        """
        return self.get_person("author")

    @property
    def maintainer(self) -> Optional[dict]:
        """
        Semantics same as `author`, but containing information
        about the maintainer of the package
        """
        return self.get_person("maintainer")

    @property
    def license(self):
        return self.optional_str("license")

    @property
    def resources(self):
        if "resources" in self.target_config:
            resources = self.target_config["resources"]
            if not isinstance(resources, dict):
                msg = f"Field `{self._BASE}.resources` must be a dictionary"
                raise TypeError(msg)
            return resources
        return None

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
        return self.optional_str("kicad_version_max")

    @property
    def tags(self) -> Optional[list[str]]:
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
