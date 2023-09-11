# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
import os
import shutil
import tempfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest


@pytest.fixture(scope="session", autouse=True)
def isolation() -> Generator[Path, None, None]:
    with TemporaryDirectory() as d:
        workdir = Path(d).resolve()
        origin = os.getcwd()
        os.chdir(workdir)
        yield workdir
        os.chdir(origin)


@pytest.fixture
def fake_project(isolation):
    src_dir = f"{isolation}/src"
    os.mkdir(src_dir)
    icon = tempfile.NamedTemporaryFile(dir=src_dir, delete=False)
    sources = [
        tempfile.NamedTemporaryFile(dir=src_dir, delete=False, suffix=".py")
        for _ in range(5)
    ]
    yield icon, sources
    shutil.rmtree(src_dir)


@pytest.fixture
def dist_dir(isolation):
    dist_dir = f"{isolation}/dist"
    os.mkdir(dist_dir)
    yield dist_dir
    shutil.rmtree(dist_dir)
