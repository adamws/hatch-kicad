# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
import json
import os
import re
import shutil
import tempfile
import zipfile
from pathlib import Path

import pytest

from hatch_kicad.build import KicadBuilder
from hatch_kicad.repository import KicadRepositoryHook

from .utils import assert_zip_content, build_config, merge_dicts


@pytest.fixture
def fake_artifacts(request, dist_dir):
    test_dir = Path(request.module.__file__).parent
    shutil.copy(f"{test_dir}/example.zip", dist_dir)
    metadata = f"{dist_dir}/metadata.json"
    with open(metadata, "w") as f:
        json.dump({}, f)
    yield f"{dist_dir}/example.zip", metadata
    # all files removed with `dist_dir`


def test_repository_url(isolation):
    url = "https://foo.bar"
    config = {"repository_url": url}
    build_hook = KicadRepositoryHook(str(isolation), config, None, None, "", "")
    assert build_hook.repository_url == url


def test_repository_wrong_type(isolation):
    config = {"repository_url": True}
    build_hook = KicadRepositoryHook(str(isolation), config, None, None, "", "")
    with pytest.raises(
        TypeError,
        match="Option `repository_url` for build hook "
        "`kicad-repository` must be a string",
    ):
        _ = build_hook.repository_url


def test_repository_url_fallback(isolation):
    config = merge_dicts(
        {"project": {"name": "plugin", "version": "0.1.0"}},
        build_config(
            {
                "download_url": "http://foo.bar/{zip_name}",
                "status": "stable",
            }
        ),
    )
    builder = KicadBuilder(str(isolation), config=config)
    build_hook = KicadRepositoryHook(str(isolation), {}, builder.config, None, "", "")
    # if `repository_url` not set, try to use parent path of `download_url`
    assert build_hook.repository_url == "http://foo.bar"


def test_repository_url_fallback_missing(isolation):
    config = {"project": {"name": "plugin", "version": "0.1.0"}}
    builder = KicadBuilder(str(isolation), config=config)
    build_hook = KicadRepositoryHook(str(isolation), {}, builder.config, None, "", "")
    with pytest.raises(
        ValueError,
        match="Option `repository_url` for build hook "
        "`kicad-repository` not found and unable to use "
        "`tool.hatch.build.targets.kicad-package.download_url` value to "
        "determine default",
    ):
        _ = build_hook.repository_url


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<!doctype html><meta charset=utf-8><title>html</title>",
    ],
)
def test_html_data_file(isolation, html):
    with tempfile.NamedTemporaryFile() as f:
        f.write(html.encode())
        f.seek(0)
        config = {"html_data": f.name}
        build_hook = KicadRepositoryHook(str(isolation), config, None, None, "", "")
        assert build_hook.html_data == html


def test_html_data_wrong_type(isolation):
    config = {"html_data": True}
    build_hook = KicadRepositoryHook(str(isolation), config, None, None, "", "")
    with pytest.raises(
        TypeError,
        match="Option `html_data` for build hook "
        "`kicad-repository` must be a string",
    ):
        _ = build_hook.html_data


def test_finalize(isolation, dist_dir, fake_project, fake_artifacts):
    icon, _ = fake_project
    archive, _ = fake_artifacts
    config = merge_dicts(
        {"project": {"name": "Plugin", "version": "0.1.0"}},
        build_config(
            {
                "reproducible": True,
                "icon": icon.name,
                "author": {"name": "bar", "email": "bar@domain"},
                "identifier": "id",
                "download_url": "http://foo.bar/{zip_name}",
                "status": "stable",
            }
        ),
    )

    builder = KicadBuilder(str(isolation), config=config)
    build_hook = KicadRepositoryHook(
        str(isolation), config, builder.config, None, dist_dir, ""
    )
    build_hook.finalize("", {}, archive)
    assert_zip_content(
        f"{dist_dir}/repository/resources.zip",
        ["id/icon.png"],
        reproducible=True,
    )
    assert zipfile.is_zipfile(f"{dist_dir}/repository/{Path(archive).name}")
    for file in ["packages.json", "repository.json", "index.html"]:
        assert os.path.isfile(f"{dist_dir}/repository/{file}")

    with open(f"{dist_dir}/repository/repository.json") as f:
        repository = json.load(f)
        assert repository["$schema"] == (
            "https://gitlab.com/kicad/code/kicad/"
            "-/raw/master/kicad/pcm/schemas/pcm.v1.schema.json#/definitions/Repository"
        )
        assert repository["maintainer"] == {
            "name": "bar",
            "contact": {"email": "bar@domain"},
        }
        assert repository["name"] == "http://foo.bar repository"
        for item, filename in [
            ("packages", "packages.json"),
            ("resources", "resources.zip"),
        ]:
            assert repository[item]["url"] == f"http://foo.bar/{filename}"
            assert re.match(r"^[A-Fa-f0-9]{64}$", repository[item]["sha256"])
            assert re.match(
                r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$",
                repository[item]["update_time_utc"],
            )
            assert isinstance(repository[item]["update_timestamp"], int)
    with open(f"{dist_dir}/repository/packages.json") as f:
        packages = json.load(f)
        # we use empty mocked `metadata.json` artifact so there is no
        # packages there:
        assert packages == {"packages": [{}]}
