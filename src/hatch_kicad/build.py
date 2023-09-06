# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import hashlib
import json
import os
import time
import zipfile
from pathlib import Path
from types import TracebackType
from typing import Any, Callable, Tuple, TypedDict

from hatchling.builders.plugin.interface import BuilderInterface
from hatchling.builders.utils import get_reproducible_timestamp

from hatch_kicad.config import KicadBuilderConfig

__all__ = ["KicadBuilder"]

ZipTime = Tuple[int, int, int, int, int, int]
READ_SIZE = 65536


class PackageMetadata(TypedDict):
    download_sha256: str
    download_size: int
    install_size: int


class ZipArchive:
    def __init__(self, file: Path, *, reproducible: bool) -> None:
        self.name = file
        self.reproducible = reproducible
        self.timestamp: int | None = (
            get_reproducible_timestamp() if reproducible else None
        )
        self.ziptime: ZipTime | None = (
            time.gmtime(self.timestamp)[0:6] if self.timestamp else None
        )
        self.zip = zipfile.ZipFile(file, "w", compression=zipfile.ZIP_DEFLATED)

    def write(self, filename: str | os.PathLike, arcname: str | os.PathLike) -> None:
        info = zipfile.ZipInfo.from_file(filename, arcname)
        if self.ziptime:
            info.date_time = self.ziptime
        with open(filename, "rb") as f:
            self.zip.writestr(info, f.read())

    def __enter__(self) -> ZipArchive:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.zip.close()


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

        # log version 'fix' occurance
        if self.metadata.version != self.config.version:
            self.app.display_warning(
                f"Found KiCad incompatible version number: {self.metadata.version}\n"
                f"Using simplified value: {self.config.version}"
            )

        try:
            metadata: dict[str, Any] = self.config.get_metadata()
            with open(metadata_target, "w") as f:
                json.dump(metadata, f, indent=4)

            found_plugin_files = False
            with ZipArchive(zip_target, reproducible=self.config.reproducible) as zipf:
                for file in self.recurse_included_files():
                    # require at least one *.py file, otherwise assume that
                    # user made an mistake in configuration
                    if not found_plugin_files and file.relative_path.endswith(".py"):
                        found_plugin_files = True
                    zipf.write(file.path, f"plugins/{file.distribution_path}")
                zipf.write(self.config.icon, "resources/icon.png")
                zipf.write(metadata_target, "metadata.json")

            if not found_plugin_files:
                self.app.display_error(
                    "No plugin files found, please check your configuration"
                )

            calculated_meta = get_package_metadata(zip_target)
            self.app.display_info("package details:")
            self.app.display_info(json.dumps(calculated_meta, indent=2))

            package_version = metadata["versions"][0]
            package_version.update(calculated_meta)
            package_version.update({"download_url": ""})
            # update with calculated metadata
            with open(metadata_target, "w") as f:
                json.dump(metadata, f, indent=4)
        except Exception as e:
            self.app.display_error(str(e))
            self.app.abort("Build failed!")

        return os.fspath(zip_target)
