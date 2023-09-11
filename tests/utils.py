# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import zipfile


def merge_dicts(x, y):
    z = x.copy()
    z.update(y)
    return z


def build_config(values):
    return {
        "tool": {
            "hatch": {
                "build": {
                    "targets": {"kicad-package": values},
                },
            },
        },
    }


def get_zip_info(zip_path) -> list[zipfile.ZipInfo]:
    content = []
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for info in zip_ref.infolist():
            content.append(info)
    return content


def assert_zip_content(
    zip_path: str, expected: list[str], *, reproducible: bool = True
):
    zip_info = get_zip_info(zip_path)
    zip_files = [z.filename for z in zip_info]
    assert len(zip_info) == len(expected)
    assert sorted(zip_files) == sorted(expected)
    if reproducible:
        for info in zip_info:
            assert info.date_time == (2020, 2, 2, 0, 0, 0)
    else:
        # non reproducible bulids should use actual file timestamps,
        # because test files are created at runtime, it should be sufficient
        # to check if year is >= 2023. This is check is required
        # to catch possible bug where `reproducible` is always on
        for info in zip_info:
            assert info.date_time[0] >= 2023
