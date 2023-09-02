from __future__ import annotations

import json
import os
import tempfile
import zipfile
from pathlib import Path

import pytest
from hatchling.builders.plugin.interface import BuilderInterface

from hatch_kicad.build import KicadBuilder, get_package_metadata


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


def test_class() -> None:
    assert issubclass(KicadBuilder, BuilderInterface)


def test_default_versions(isolation):
    builder = KicadBuilder(str(isolation))

    assert builder.get_default_versions() == ["standard"]


@pytest.mark.parametrize(
    "name,value",
    [
        ("name", "Plugin Name"),
        ("description", "Plugin Description"),
        ("description_full", "Plugin full description"),
        ("identifier", "com.github.autor.plugin-name"),
        ("status", "stable"),
        ("kicad_version", "6.0"),
    ],
)
class TestRequiredStringOptions:
    def test_option(self, name, value, isolation):
        builder = KicadBuilder(str(isolation), config=build_config({name: value}))
        assert getattr(builder.config, name) == value

    def test_option_join(self, name, value, isolation):
        builder = KicadBuilder(str(isolation), config=build_config({name: list(value)}))
        assert getattr(builder.config, name) == value

    def test_option_wrong_type(self, name, value, isolation):
        _ = value
        builder = KicadBuilder(str(isolation), config=build_config({name: True}))
        with pytest.raises(
            TypeError,
            match=f"Field `tool.hatch.build.targets.kicad-package.{name}` "
            "must be a string or list of strings",
        ):
            _ = getattr(builder.config, name)

    def test_option_missing(self, name, value, isolation):
        _ = value
        builder = KicadBuilder(str(isolation), config={})
        with pytest.raises(
            TypeError,
            match=f"Field `tool.hatch.build.targets.kicad-package.{name}` not found",
        ):
            _ = getattr(builder.config, name)


@pytest.mark.parametrize(
    "name,max_length",
    [
        ("name", 200),
        ("description", 500),
        ("description_full", 5000),
    ],
)
class TestLengthLimitedStringOptions:
    def test_option_max_length(self, name, max_length, isolation):
        config = build_config({name: max_length * "a"})
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, name) == max_length * "a"

    def test_option_too_long(self, name, max_length, isolation):
        config = build_config({name: (max_length + 1) * "a"})
        builder = KicadBuilder(str(isolation), config=config)
        with pytest.raises(
            TypeError,
            match=(
                f"Field `tool.hatch.build.targets.kicad-package.{name}` too long, "
                f"can be {max_length} character long, got {max_length + 1}"
            ),
        ):
            _ = getattr(builder.config, name)


def test_type(isolation):
    # type is always equal 'plugin'
    builder = KicadBuilder(str(isolation), config={})
    assert builder.config.type == "plugin"


@pytest.mark.parametrize(
    "person",
    ["author", "maintainer"],
)
class TestContactOptions:
    def test_contact(self, person, isolation):
        # when author/maintainer specified by `kicad-package`
        # then ignore `project.authors` / `project.maintainers`
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config({person: {"name": "bar", "email": "bar@domain"}}),
        )
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, person) == {
            "name": "bar",
            "contact": {"email": "bar@domain"},
        }

    def test_contact_more_information(self, person, isolation):
        # when author/maintainer specified by `kicad-package` it can have
        # more contact forms than just email
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config(
                {
                    person: {
                        "name": "bar",
                        "email": "bar@domain",
                        "website": "https://bar.site",
                    }
                }
            ),
        )
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, person) == {
            "name": "bar",
            "contact": {"email": "bar@domain", "website": "https://bar.site"},
        }

    def test_contact_wrong_type(self, person, isolation):
        # author/maintainer must have name
        builder = KicadBuilder(str(isolation), config=build_config({person: "bar"}))
        with pytest.raises(
            TypeError,
            match=f"Field `tool.hatch.build.targets.kicad-package.{person}` "
            "must be a dictionary",
        ):
            _ = getattr(builder.config, person)

    def test_contact_without_name(self, person, isolation):
        # author/maintainer must have name
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config({person: {"email": "bar@domain"}}),
        )
        builder = KicadBuilder(str(isolation), config=config)
        with pytest.raises(
            TypeError,
            match=f"Field `tool.hatch.build.targets.kicad-package.{person}` "
            "must have `name` property",
        ):
            _ = getattr(builder.config, person)

    def test_contact_with_only_name(self, person, isolation):
        # author/maintainer with name only should have empty contact information
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config({person: {"name": "bar"}}),
        )
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, person) == {"name": "bar", "contact": {}}

    def test_contact_fallback(self, person, isolation):
        # when author/maintainer not specified by `kicad-package`,
        # try to get first from `project.authors`/`project.maintainers`
        config = {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}}
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, person) == {
            "name": "foo",
            "contact": {"email": "foo@domain"},
        }

    def test_contact_fallback_email_missing(self, person, isolation):
        # when author/maintainer not specified by `kicad-package`,
        # try to get first from `project.authors`/`project.maintainers`,
        # if it has only name, use empty contact information
        config = {"project": {person + "s": [{"name": "foo"}]}}
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, person) == {"name": "foo", "contact": {}}

    def test_contact_fallback_missing(self, person, isolation):
        # when author not specified by `kicad-package` and `project.authors`,
        # raise an exception
        config = {"project": {"name": "Plugin", "version": "0.1.0"}}
        builder = KicadBuilder(str(isolation), config=config)
        if person == "author":
            with pytest.raises(
                TypeError,
                match=f"Field `tool.hatch.build.targets.kicad-package.{person}` not "
                f"found, failed to get author from `project.{person}s` value",
            ):
                _ = getattr(builder.config, person)
        # maintainer is optional so do nothing is fallback missing
        elif person == "maintainer":
            assert getattr(builder.config, person) is None
        else:
            raise RuntimeError

    def test_contact_fallback_email_only(self, person, isolation):
        config = {"project": {person + "s": [{"email": "foo@domain"}]}}
        builder = KicadBuilder(str(isolation), config=config)
        # when author not specified by `kicad-package`
        # and first from `project.authors` has email only,
        # raise an exception
        if person == "author":
            with pytest.raises(
                TypeError,
                match=f"Field `tool.hatch.build.targets.kicad-package.{person}` not "
                f"found, failed to get {person} from `project.{person}s` value",
            ):
                _ = getattr(builder.config, person)
        # maintainer is optional so do nothing is fallback is not valid
        elif person == "maintainer":
            assert getattr(builder.config, person) is None
        else:
            raise RuntimeError


def test_license(isolation):
    config = merge_dicts(
        {"project": {"name": "Plugin", "license": "gpl-3.0"}},
        build_config({"license": "MIT"}),
    )
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.license == "MIT"


def test_license_wrong_value(isolation):
    config = merge_dicts(
        {"project": {"name": "Plugin", "license": "gpl-3.0"}},
        build_config({"license": "unrecognized"}),
    )
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Invalid license value: `unrecognized`\n"
        "For the list of the supported licenses visit: "
        "https://github.com/adamws/hatch-kicad/blob/master"
        "/src/hatch_kicad/licenses/supported.py",
    ):
        _ = builder.config.license


def test_license_wrong_type(isolation):
    config = merge_dicts(
        {"project": {"name": "Plugin", "license": "gpl-3.0"}},
        build_config({"license": True}),
    )
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.license` "
        "must be a string or list of strings",
    ):
        _ = builder.config.license


def test_license_fallback(isolation):
    config = {"project": {"name": "Plugin", "license": {"text": "MIT"}}}
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.license == "MIT"


def test_license_fallback_missing(isolation):
    config = {"project": {"name": "Plugin"}}
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match=(
            "Field `tool.hatch.build.targets.kicad-package.license` not found, "
            "failed to deduce license from `project.license` value.\n"
            'Define `license = {text = "<value>"} in `project` or '
            '`license = "<value>" in `tool.hatch.build.targets.kicad-package'
        ),
    ):
        _ = builder.config.license


def test_resources(isolation):
    config = merge_dicts(
        {"project": {"name": "Plugin", "urls": {"Website": "https://foo.site"}}},
        build_config({"resources": {"Website": "https://bar.site"}}),
    )
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.resources == {"Website": "https://bar.site"}


def test_resources_many(isolation):
    config = merge_dicts(
        {"project": {"name": "Plugin", "urls": {"Website": "https://foo.site"}}},
        build_config(
            {
                "resources": {
                    "Website": "https://bar.site",
                    "Bug Tracker": "https://bugs.bar.site",
                }
            }
        ),
    )
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.resources == {
        "Website": "https://bar.site",
        "Bug Tracker": "https://bugs.bar.site",
    }


def test_resources_wrong_type(isolation):
    config = merge_dicts(
        {"project": {"name": "Plugin", "urls": {"Website": "https://foo.site"}}},
        build_config({"resources": "https://bar.site"}),
    )
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.resources` must be a dict",
    ):
        _ = builder.config.resources


def test_resources_fallback(isolation):
    config = {"project": {"name": "Plugin", "urls": {"Website": "https://foo.site"}}}
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.resources == {"Website": "https://foo.site"}


def test_resources_fallback_missing(isolation):
    config = {"project": {"name": "Plugin"}}
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.resources == {}


def test_keep_on_update(isolation):
    builder = KicadBuilder(str(isolation), config={})
    assert builder.config.keep_on_update is None


def test_status_wrong_value(isolation):
    builder = KicadBuilder(str(isolation), config=build_config({"status": "unknown"}))
    with pytest.raises(
        TypeError,
        match=(
            "Invalid `tool.hatch.build.targets.kicad-package.status` value.\n"
            "`status` must be one of: `stable`, `testing`, "
            "`development` or `deprecated`."
        ),
    ):
        _ = builder.config.status


def test_kicad_version_max(isolation):
    config = build_config({"kicad_version_max": "6.0"})
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.kicad_version_max == "6.0"


def test_kicad_version_max_wrong_type(isolation):
    config = build_config({"kicad_version_max": True})
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.kicad_version_max` "
        "must be a string or list of strings",
    ):
        _ = builder.config.kicad_version_max


def test_kicad_version_max_missing(isolation):
    builder = KicadBuilder(str(isolation), config={})
    assert builder.config.kicad_version_max == ""


def test_tags(isolation):
    config = build_config({"tags": ["tag1", "tag2"]})
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.tags == ["tag1", "tag2"]


def test_tags_missing(isolation):
    builder = KicadBuilder(str(isolation), config={})
    assert builder.config.tags == []


def test_tags_wrong_type(isolation):
    config = build_config({"tags": [True]})
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.tags` "
        "must be list of strings",
    ):
        _ = builder.config.tags


def test_icon(isolation):
    tf = tempfile.NamedTemporaryFile()
    config = build_config({"icon": tf.name})
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.icon == Path(tf.name)


def test_icon_missing(isolation):
    builder = KicadBuilder(str(isolation), config={})
    with pytest.raises(
        TypeError, match="Field `tool.hatch.build.targets.kicad-package.icon` not found"
    ):
        _ = builder.config.icon


def test_icon_does_not_exist(isolation):
    config = build_config({"icon": "src/icon.png"})
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.icon` "
        "must point to a file",
    ):
        _ = builder.config.icon


def test_icon_wrong_type(isolation):
    config = build_config({"icon": ["src/icon.png"]})
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.icon` must be a string",
    ):
        _ = builder.config.icon


def test_get_metadata(isolation):
    data = {
        "name": "Plugin Name",
        "description": "Short Decription",
        "description_full": ["Full multiline\n", "description"],
        "identifier": "com.plugin.identifier",
        "author": {"name": "bar", "email": "bar@domain"},
        "license": "MIT",
        "status": "stable",
        "kicad_version": "6.0",
    }
    config = merge_dicts(
        {"project": {"name": "Plugin", "version": "0.0.1"}}, build_config(data)
    )
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.get_metadata() == {
        "$schema": "https://go.kicad.org/pcm/schemas/v1",
        "name": "Plugin Name",
        "description": "Short Decription",
        "description_full": "Full multiline\ndescription",
        "identifier": "com.plugin.identifier",
        "type": "plugin",
        "author": {"name": "bar", "contact": {"email": "bar@domain"}},
        "license": "MIT",
        "resources": {},
        "versions": [{"kicad_version": "6.0", "status": "stable", "version": "0.0.1"}],
    }


def test_package_metadata_calculation(request):
    test_dir = Path(request.module.__file__).parent
    metadata = get_package_metadata(f"{test_dir}/example.zip")
    assert (
        metadata["download_sha256"]
        == "b97d51ed4b8f3efcf53fffbfdc6a353fe516da1efbf807b2750ef3873e8e63ef"
    )
    assert metadata["download_size"] == 174
    assert metadata["install_size"] == 10


def get_zip_contents(zip_path) -> list[str]:
    content = []
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for file_name in zip_ref.namelist():
            content.append(file_name)
    return content


def test_build_standard(isolation):
    dist_dir = f"{isolation}/dist"
    src_dir = f"{isolation}/src"
    os.mkdir(dist_dir)
    os.mkdir(src_dir)
    icon = tempfile.NamedTemporaryFile(dir=src_dir)
    sources = [tempfile.NamedTemporaryFile(dir=src_dir, suffix=".py") for _ in range(5)]
    data = {
        "name": "Plugin Name",
        "description": "Short Decription",
        "description_full": ["Full multiline\n", "description"],
        "identifier": "com.plugin.identifier",
        "author": {"name": "bar", "email": "bar@domain"},
        "license": "MIT",
        "status": "stable",
        "kicad_version": "6.0",
        "icon": icon.name,
        "sources": ["src"],
        "include": ["src/*.py"],
    }
    config = merge_dicts(
        {"project": {"name": "Plugin", "version": "0.0.1"}}, build_config(data)
    )
    builder = KicadBuilder(str(isolation), config=config)
    builder.build_standard(dist_dir)
    with open(f"{dist_dir}/metadata.json") as f:
        metadata_result = json.load(f)
        version = metadata_result["versions"][0]
        assert "download_sha256" in version
        assert "download_size" in version
        assert "install_size" in version
        del version["download_sha256"]
        del version["download_size"]
        del version["install_size"]
        assert metadata_result == builder.config.get_metadata()

    in_zip = get_zip_contents(f"{isolation}/dist/Plugin-0.0.1.zip")
    expected = ["resources/icon.png", "metadata.json"]
    for s in sources:
        name = Path(s.name).name
        expected.append(f"plugin/{name}")
    assert len(in_zip) == len(expected) and sorted(in_zip) == sorted(expected)


def test_build_standard_wrong_config(monkeypatch, isolation):
    def mock_abort(*args, **kwargs):
        _ = args, kwargs
        msg = "Abort called"
        raise Exception(msg)

    monkeypatch.setattr("hatchling.bridge.app.Application.abort", mock_abort)
    config = {"project": {"name": "Plugin", "version": "0.1.0"}}
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(Exception, match="Abort called"):
        builder.build_standard(str(isolation))
