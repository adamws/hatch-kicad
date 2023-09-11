# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path
from types import MappingProxyType
from unittest.mock import Mock

import pytest
from hatchling.builders.plugin.interface import BuilderInterface

from hatch_kicad.build import KicadBuilder, get_package_metadata

from .utils import assert_zip_content, build_config, merge_dicts


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
            ValueError,
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
            ValueError,
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

    def test_contact_name_too_long(self, person, isolation):
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config({person: {"name": 501 * "a", "email": "bar@domain"}}),
        )
        builder = KicadBuilder(str(isolation), config=config)
        with pytest.raises(
            ValueError,
            match=f"Field `tool.hatch.build.targets.kicad-package.{person}` "
            "`name` property too long, can be 500 character long, got 501",
        ):
            _ = getattr(builder.config, person)

    def test_contact_details_wrong_format_key(self, person, isolation):
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config({person: {"name": "bar", "---email": "bar@domain"}}),
        )
        builder = KicadBuilder(str(isolation), config=config)
        regex_pattern = r"^[a-zA-Z][-a-zA-Z0-9 ]{0,48}[a-zA-Z0-9]$"
        with pytest.raises(
            ValueError,
            match=re.escape(
                f"Field `tool.hatch.build.targets.kicad-package.{person}` "
                "`---email` property has invalid format, must match following regular "
                f"expression: `{regex_pattern}`"
            ),
        ):
            _ = getattr(builder.config, person)

    def test_contact_details_too_long(self, person, isolation):
        config = merge_dicts(
            {"project": {person + "s": [{"email": "foo@domain", "name": "foo"}]}},
            build_config({person: {"name": "bar", "email": 501 * "a"}}),
        )
        builder = KicadBuilder(str(isolation), config=config)
        with pytest.raises(
            ValueError,
            match=f"Field `tool.hatch.build.targets.kicad-package.{person}` "
            "`email` property too long, can be 500 character long, got 501",
        ):
            _ = getattr(builder.config, person)

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

    def test_contact_fallback_name_too_long(self, person, isolation):
        # if parameters extended it would requrie test adjustment:
        assert person in ["author", "maintainer"]
        config = {
            "project": {person + "s": [{"email": "foo@domain", "name": 501 * "a"}]}
        }
        builder = KicadBuilder(str(isolation), config=config)
        if person == "author":
            with pytest.raises(
                ValueError,
                match=re.escape(
                    f"Field `project.{person}s[0]` `name` property "
                    "too long, can be 500 character long, got 501"
                ),
            ):
                _ = getattr(builder.config, person)
        # maintainer is optional so do nothing is fallback is not valid
        else:
            assert getattr(builder.config, person) is None

    def test_contact_fallback_email_missing(self, person, isolation):
        # when author/maintainer not specified by `kicad-package`,
        # try to get first from `project.authors`/`project.maintainers`,
        # if it has only name, use empty contact information
        config = {"project": {person + "s": [{"name": "foo"}]}}
        builder = KicadBuilder(str(isolation), config=config)
        assert getattr(builder.config, person) == {"name": "foo", "contact": {}}

    def test_contact_fallback_missing(self, person, isolation):
        # if parameters extended it would requrie test adjustment:
        assert person in ["author", "maintainer"]
        config = {"project": {"name": "Plugin", "version": "0.1.0"}}
        builder = KicadBuilder(str(isolation), config=config)
        # when author not specified by `kicad-package` and `project.authors`,
        # raise an exception
        if person == "author":
            with pytest.raises(
                ValueError,
                match=f"Field `tool.hatch.build.targets.kicad-package.{person}` not "
                f"found, failed to get author from `project.{person}s` value",
            ):
                _ = getattr(builder.config, person)
        # maintainer is optional so do nothing is fallback missing
        else:
            assert getattr(builder.config, person) is None

    def test_contact_fallback_email_only(self, person, isolation):
        # if parameters extended it would requrie test adjustment:
        assert person in ["author", "maintainer"]
        config = {"project": {person + "s": [{"email": "foo@domain"}]}}
        builder = KicadBuilder(str(isolation), config=config)
        # when author not specified by `kicad-package`
        # and first from `project.authors` has email only,
        # raise an exception
        if person == "author":
            with pytest.raises(
                ValueError,
                match=f"Field `tool.hatch.build.targets.kicad-package.{person}` not "
                f"found, failed to get {person} from `project.{person}s` value",
            ):
                _ = getattr(builder.config, person)
        # maintainer is optional so do nothing is fallback is not valid
        else:
            assert getattr(builder.config, person) is None


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
        ValueError,
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
        ValueError,
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
        ValueError,
        match=(
            "Invalid `tool.hatch.build.targets.kicad-package.status` value.\n"
            "`status` must be one of: `stable`, `testing`, "
            "`development` or `deprecated`."
        ),
    ):
        _ = builder.config.status


def test_status_env_substitution(isolation, monkeypatch):
    monkeypatch.setenv("HATCH_KICAD_STATUS", "stable")
    builder = KicadBuilder(
        str(isolation),
        config=build_config({"status": "{env:HATCH_KICAD_STATUS:development}"}),
    )
    assert builder.config.status == "stable"


def test_status_env_substitution_default(isolation):
    builder = KicadBuilder(
        str(isolation),
        config=build_config({"status": "{env:HATCH_KICAD_STATUS:development}"}),
    )
    assert builder.config.status == "development"


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


@pytest.mark.parametrize(
    "name",
    ["kicad_version", "kicad_version_max"],
)
def test_version_wrong_format(name, isolation):
    config = build_config({name: "6.0.0.1"})
    builder = KicadBuilder(str(isolation), config=config)
    regex_pattern = r"^\d{1,4}(\.\d{1,4}(\.\d{1,6})?)?$"
    with pytest.raises(
        ValueError,
        match=re.escape(
            f"Field `tool.hatch.build.targets.kicad-package.{name}` has "
            "invalid format, must match following regular "
            f"expression: `{regex_pattern}`"
        ),
    ):
        _ = getattr(builder.config, name)


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
        ValueError,
        match="Field `tool.hatch.build.targets.kicad-package.icon` not found",
    ):
        _ = builder.config.icon


def test_icon_does_not_exist(isolation):
    config = build_config({"icon": "src/icon.png"})
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        ValueError,
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


def test_version(isolation):
    config = {"project": {"name": "Plugin", "version": "0.1.0"}}
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.version == "0.1.0"


def test_version_simplification(isolation):
    config = {"project": {"name": "Plugin", "version": "0.1.0-alpha"}}
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.version == "0.1.0"


def test_version_unrecoverable_illegal_format(isolation):
    config = {"project": {"name": "Plugin", "version": "dev0.1.0"}}
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        ValueError,
        match=(
            "Invalid version `dev0.1.0` from field `project.version`, "
            "see https://peps.python.org/pep-0440/"
        ),
    ):
        _ = builder.config.version


def test_download_url(isolation):
    url = "https://example.com/dist/package.zip"
    config = merge_dicts(
        {"project": {"name": "plugin", "version": "0.0.1"}},
        build_config({"download_url": url, "status": "stable"}),
    )
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.download_url == url


def test_download_url_wrong_type(isolation):
    config = build_config({"download_url": True})
    builder = KicadBuilder(str(isolation), config=config)
    with pytest.raises(
        TypeError,
        match="Field `tool.hatch.build.targets.kicad-package.download_url` "
        "must be a string",
    ):
        _ = builder.config.download_url


def test_download_url_missing(isolation):
    builder = KicadBuilder(str(isolation), config={})
    assert builder.config.download_url == ""


@pytest.mark.parametrize(
    "envs,download_url,expected_url",
    [
        (
            {"PLUGIN_DIR": "baz", "STATUS": "stable"},
            "test/{env:PLUGIN_DIR:bar}/{status}/v{version}/{zip_name}",
            "test/baz/stable/v0.0.1/plugin-0.0.1.zip",
        ),
        (
            {},
            "test/{env:PLUGIN_DIR:bar}/{status}/v{version}/{zip_name}",
            "test/bar/development/v0.0.1/plugin-0.0.1.zip",
        ),
        (
            {"PLUGIN_URL": "test/{status}/plugin.zip"},
            "{env:PLUGIN_URL:test/default/{zip_name}}",
            "test/development/plugin.zip",
        ),
        (
            {"PLUGIN_URL": "test/{status}/plugin.zip", "STATUS": "stable"},
            "{env:PLUGIN_URL:test/default/{zip_name}}",
            "test/stable/plugin.zip",
        ),
        (
            {},
            "{env:PLUGIN_URL:test/default/{zip_name}}",
            "test/default/plugin-0.0.1.zip",
        ),
    ],
)
def test_download_url_substitution(
    isolation, monkeypatch, envs, download_url, expected_url
):
    for k, v in envs.items():
        monkeypatch.setenv(k, v)
    data = {
        "status": "{env:STATUS:development}",
        "download_url": download_url,
    }
    config = merge_dicts(
        {"project": {"name": "plugin", "version": "0.0.1"}}, build_config(data)
    )
    builder = KicadBuilder(str(isolation), config=config)
    assert builder.config.download_url == expected_url


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


class TestBuildStandard:
    _CONFIG_BASE = MappingProxyType(
        {
            "name": "Plugin Name",
            "description": "Short Decription",
            "description_full": ["Full multiline\n", "description"],
            "identifier": "com.plugin.identifier",
            "author": {"name": "bar", "email": "bar@domain"},
            "license": "MIT",
            "status": "stable",
            "kicad_version": "6.0",
        }
    )

    def assert_versions(self, metadata: dict, **kwargs):
        # metadata should have single version with `download_sha256`,
        # `download_size` and `install_size` keys and non-empty
        # values (calculating these values is tested separately by known zip file
        # so it can be skipped here for fake-generated one)
        # it also should have empty `download_url` (just as a reminder for a user
        # that this is required for submitting to PCM - setting this via
        # configuration not supported yet)
        assert "versions" in metadata
        versions = metadata["versions"]
        assert len(versions) == 1
        for k in ["download_sha256", "download_size", "install_size"]:
            assert k in versions[0]
            assert versions[0][k]
        assert "download_url" in versions[0]
        assert versions[0]["download_url"] == ""
        for k, v in kwargs.items():
            assert versions[0][k] == v

    def filter_dict(self, data: dict, ignore: list[str]) -> dict:
        return {k: v for k, v in data.items() if k not in ignore}

    @pytest.mark.parametrize(
        "reproducible",
        [True, False],
        ids=lambda val: "reproducible" if val else "non-reproducible",
    )
    def test_build_minimal_config(
        self, reproducible, isolation, fake_project, dist_dir
    ):
        icon, sources = fake_project
        data = merge_dicts(
            self._CONFIG_BASE,
            {
                "icon": icon.name,
                "sources": ["src"],
                "include": ["src/*.py"],
                "reproducible": reproducible,
            },
        )
        config = merge_dicts(
            {"project": {"name": "Plugin", "version": "0.0.1"}}, build_config(data)
        )
        builder = KicadBuilder(str(isolation), config=config)
        builder.build_standard(dist_dir)
        with open(f"{dist_dir}/metadata.json") as f:
            metadata_result = json.load(f)
            self.assert_versions(
                metadata_result, version="0.0.1", status="stable", kicad_version="6.0"
            )
            # assert that produced json contains same data as internall config metadata
            # (ignoring version which contains dynamic data sha and sizes)
            assert self.filter_dict(metadata_result, ["versions"]) == self.filter_dict(
                builder.config.get_metadata(), ["versions"]
            )

        expected = ["resources/icon.png", "metadata.json"]
        for s in sources:
            name = Path(s.name).name
            expected.append(f"plugins/{name}")
        assert_zip_content(
            f"{isolation}/dist/Plugin-0.0.1.zip", expected, reproducible=reproducible
        )

    def test_build_failed_maintainer(
        self, monkeypatch, isolation, fake_project, dist_dir
    ):
        abort_mock = Mock()
        monkeypatch.setattr("hatchling.bridge.app.Application.abort", abort_mock)
        display_error_mock = Mock()
        monkeypatch.setattr(
            "hatchling.bridge.app.Application.display_error", display_error_mock
        )
        icon, _ = fake_project
        data = merge_dicts(
            self._CONFIG_BASE,
            # if illegal maintainer is explicitly declared in `kicad-pacakge` target,
            # then raise an exception even though it is not required metadata field
            {"icon": icon.name, "maintainer": {"name": 501 * "a"}},
        )
        config = merge_dicts(
            {"project": {"name": "Plugin", "version": "0.0.1"}}, build_config(data)
        )
        builder = KicadBuilder(str(isolation), config=config)
        builder.build_standard(dist_dir)
        expected_error = (
            "Field `tool.hatch.build.targets.kicad-package.maintainer` `name` "
            "property too long, can be 500 character long, got 501"
        )
        display_error_mock.assert_called_once_with(expected_error)
        abort_mock.assert_called_once_with("Build failed!")

    def test_build_ignores_failed_maintainer_fallback(
        self, isolation, fake_project, dist_dir
    ):
        icon, _ = fake_project
        data = merge_dicts(
            self._CONFIG_BASE,
            {"icon": icon.name, "sources": ["src"], "include": ["src/*.py"]},
        )
        config = merge_dicts(
            {
                "project": {
                    "name": "Plugin",
                    "version": "0.0.1",
                    # this maintainer has illegal name but we should ignore it
                    # since maintainer is not required metadata field
                    # and it just an optional fallback (maintainer not defined
                    # by `kicad-package` target)
                    "maintainers": [{"name": 501 * "a"}],
                }
            },
            build_config(data),
        )
        builder = KicadBuilder(str(isolation), config=config)
        builder.build_standard(dist_dir)
        with open(f"{dist_dir}/metadata.json") as f:
            metadata_result = json.load(f)
            assert "maintainer" not in metadata_result
            assert self.filter_dict(metadata_result, ["versions"]) == self.filter_dict(
                builder.config.get_metadata(), ["versions"]
            )

    def test_build_standard_wrong_config(self, monkeypatch, isolation):
        mock = Mock()
        monkeypatch.setattr("hatchling.bridge.app.Application.abort", mock)
        config = {"project": {"name": "Plugin", "version": "0.1.0"}}
        builder = KicadBuilder(str(isolation), config=config)
        builder.build_standard(str(isolation))
        mock.assert_called_once_with("Build failed!")

    def test_build_incompatible_version(
        self, monkeypatch, isolation, fake_project, dist_dir
    ):
        mock = Mock()
        monkeypatch.setattr("hatchling.bridge.app.Application.display_warning", mock)
        icon, _ = fake_project
        incompatible_version = "0.7.dev8+g2d9da6b.d20230903"
        data = merge_dicts(
            self._CONFIG_BASE,
            {"icon": icon.name, "sources": ["src"], "include": ["src/*.py"]},
        )
        config = merge_dicts(
            {"project": {"name": "Plugin", "version": incompatible_version}},
            build_config(data),
        )
        builder = KicadBuilder(str(isolation), config=config)
        builder.build_standard(dist_dir)
        with open(f"{dist_dir}/metadata.json") as f:
            metadata_result = json.load(f)
            self.assert_versions(
                metadata_result, version="0.7", status="stable", kicad_version="6.0"
            )
        mock.assert_called_once_with(
            f"Found KiCad incompatible version number: {incompatible_version}\n"
            "Using simplified value: 0.7"
        )

    def test_warn_missing_files(self, monkeypatch, isolation, fake_project, dist_dir):
        mock = Mock()
        monkeypatch.setattr("hatchling.bridge.app.Application.display_error", mock)
        icon, _ = fake_project
        data = merge_dicts(
            self._CONFIG_BASE,
            {
                "icon": icon.name,
                "include": ["src/*.txt"],
            },
        )
        config = merge_dicts(
            {"project": {"name": "Plugin", "version": "0.0.1"}}, build_config(data)
        )
        builder = KicadBuilder(str(isolation), config=config)
        builder.build_standard(dist_dir)
        mock.assert_called_once_with(
            "No plugin files found, please check your configuration"
        )
