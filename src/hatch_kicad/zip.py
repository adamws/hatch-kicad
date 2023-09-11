# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import time
import zipfile
from pathlib import Path
from types import TracebackType
from typing import Tuple

from hatchling.builders.utils import get_reproducible_timestamp

__all__ = ["ZipArchive"]

ZipTime = Tuple[int, int, int, int, int, int]


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

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.zip.close()
