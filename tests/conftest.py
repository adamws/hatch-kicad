import os
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
