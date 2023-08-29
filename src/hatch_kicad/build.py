# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path
from typing import Any, Callable, TypedDict

from hatchling.builders.plugin.interface import BuilderInterface

from hatch_kicad.config import KicadBuilderConfig

__all__ = ["KicadBuilder"]

READ_SIZE = 65536


class PackageMetadata(TypedDict):
    download_sha256: str
    download_size: int
    install_size: int


def getsha256(filename) -> str:
    sha256 = hashlib.sha256()
    with open(filename, "rb") as f:
        while data := f.read(READ_SIZE):
            sha256.update(data)
    return sha256.hexdigest()


def get_package_metadata(filename) -> PackageMetadata:
    z = zipfile.ZipFile(filename, "r")
    install_size = sum(entry.file_size for entry in z.infolist() if not entry.is_dir())
    return {
        "download_sha256": getsha256(filename),
        "download_size": os.path.getsize(filename),
        "install_size": install_size,
    }


class KicadBuilder(BuilderInterface):
    PLUGIN_NAME = "kicad-package"

    @classmethod
    def get_config_class(cls):
        return KicadBuilderConfig

    def get_version_api(self) -> dict[str, Callable[..., str]]:
        return {"standard": self.build_standard}

    def build_standard(self, directory: str, **build_data: Any) -> str:
        project_name = self.normalize_file_name_component(self.metadata.core.raw_name)
        zip_name = f"{project_name}-{self.metadata.version}.zip"
        zip_target = Path(directory, zip_name)
        metadata_target = Path(directory, "metadata.json")

        metadata = None
        try:
            metadata = self.__get_metadata()
            with open(metadata_target, "w") as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            self.app.display_error(str(e))
            self.app.abort("Build failed!")

        with zipfile.ZipFile(zip_target, "w", zipfile.ZIP_DEFLATED) as zipf:
            for file in self.recurse_included_files():
                zipf.write(file.path, f"plugin/{file.distribution_path}")
            if "icon" in self.target_config:
                zipf.write(self.target_config["icon"], "resources/icon.png")
            zipf.write(metadata_target, "metadata.json")

        if metadata:
            package_version = metadata["versions"][0]
            package_version.update(get_package_metadata(zip_target))
            self.app.display_info("package details:")
            self.app.display_info(json.dumps(package_version, indent=4))
            # update with calculated metadata
            with open(metadata_target, "w") as f:
                json.dump(metadata, f, indent=4)

        return os.fspath(zip_target)

    def __get_first_person_data(self, persons, name: str):
        # KiCad schema permit only one author/maintainer so take the first one,
        # It also requires contact information which is not mandatory
        # in python package metadata, if email not found use default
        # placeholder
        if persons and "name" in persons[0]:
            return {
                "name": persons[0]["name"],
                "contact": {"email": persons[0].get("email", "-")},
            }
        else:
            msg = (
                f"Field `tool.hatch.build.targets.kicad-package.{name}` not found, "
                "failed to deduce author from `project.{name}s` value"
            )
            raise TypeError(msg)

    def __get_metadata(self) -> dict[str, Any]:
        # if `self.config` does not contain `author` or `maintainer`,
        # try to deduce it from `self.metadata.core.authors`
        # and `self.metadata.core.maintainers`
        if not (author := self.config.author):
            authors = self.metadata.core.authors
            author = self.__get_first_person_data(authors, "author")
        if not (maintainer := self.config.maintainer):
            maintainers = self.metadata.core.maintainers
            try:
                maintainer = self.__get_first_person_data(maintainers, "maintainer")
            except Exception:
                # maintainer is not required so if can't be deduce nothing happens
                maintainer = None
        # if `self.config` does not contain `license`,
        # try to deduce it from `self.metadata.core.license`
        if not (license_str := self.config.license):
            if not (license_str := self.metadata.core.license):
                msg = (
                    'Field `tool.hatch.build.targets.kicad-package.license` not found, '
                    'failed to deduce license from `project.license` value.\n'
                    'Define `license = {text = "<value>"} in `project` or '
                    '`license = "<value>" in `tool.hatch.build.targets.kicad-package'
                )
                raise TypeError(msg)
        # if `self.config` does not contain `resources`,
        # try to deduce it from `self.metadata.core.urls`
        if not (resources := self.config.resources):
            if not (resources := self.metadata.core.urls):
                # `resources` are not mandatory so if can't be deduced nothing happens
                resources = None

        metadata = {
            "$schema": "https://go.kicad.org/pcm/schemas/v1",
            "name": self.config.name,
            "description": self.config.description,
            "description_full": self.config.description_full,
            "identifier": self.config.identifier,
            "type": self.config.type,
            "author": author,
            "maintainer": maintainer,
            "license": license_str,
            "resources": resources,
            "tags": self.config.tags,
            "versions": [
                {
                    "version": self.metadata.version,
                    "status": self.config.status,
                    "kicad_version": self.config.kicad_version,
                    "kicad_version_max": self.config.kicad_version_max,
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
