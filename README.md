# hatch-kicad

|         |                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ---     | ---                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| CI/CD   | [![CI - Main](https://github.com/adamws/hatch-kicad/actions/workflows/main.yml/badge.svg)](https://github.com/adamws/hatch-kicad/actions/workflows/main.yml) [![Coverage Status](https://coveralls.io/repos/github/adamws/hatch-kicad/badge.svg?branch=master)](https://coveralls.io/github/adamws/hatch-kicad?branch=master)                                                                                                                                                                                                                                                                                      |
| Package | [![PyPI - Version](https://img.shields.io/pypi/v/hatch-kicad.svg)](https://pypi.org/project/hatch-kicad) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/hatch-kicad.svg)](https://pypi.org/project/hatch-kicad)                                                                                                                                                                                                                                                                                                                                                                                  |
| Meta    | [![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch) [![linting - Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff) [![code style - Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![types - Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://github.com/python/mypy) [![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/) |

-----

**[Hatch](https://hatch.pypa.io/latest)** plugin to build **[KiCad](https://www.kicad.org/)** addon packages.

**Table of Contents**

- [Global dependency](#global-dependency)
- [Builder](#builder)
  - [Options](#options)
  - [How to run](#how-to-run)
- [License](#license)

## Global dependency

Add `hatch-kicad` within the `build-system.requires` field in your `pyproject.toml` file.

```toml
[build-system]
requires = ["hatchling", "hatch-kicad"]
build-backend = "hatchling.build"
```

## Builder

The [builder plugin](https://hatch.pypa.io/latest/plugins/builder/reference/) name is `kicad-package`.

### Options

Specify package metadata and [file selection](https://hatch.pypa.io/latest/config/build/#file-selection) in your `pyproject.toml` file.
Depending on the project structure, it may be required to [rewrite relative paths](https://hatch.pypa.io/latest/config/build/#rewriting-paths).
In this example it is shown how to remove `src/` path prefix:

```toml
[tool.hatch.build.kicad-package]
# rewrite paths using `source` option, src/a.py will become a.py
# which will be copied to `plugin` directory inside the zip package
sources = ["src"]
include = [
  "src/*.py",
  "src/version.txt",
  "src/icon.png",
]
# icon (regardless of the filename) will be copied to
# resources/icon.png inside the zip package
icon = "resources/icon.png"
name = "Plugin name"
# ...remaining required options
```

When in doubt check the plugin archive content, it must look like this:

```shell
Archive root
├── plugins
   ├── __init__.py
   ├── ...
├── resources
   ├── icon.png
├── metadata.json
```

> [!IMPORTANT]
> `metadata.json` is created and packaged by plugin. Do not create it manually.

### Option details

| Option              | Type                                                        | Default                                                                                                                                                                                                                                                                                                              | Description                                                                                                                                                                                                                                                                                                                                    |
| ------------        | -------                                                     | --------------                                                                                                                                                                                                                                                                                                       | --------------------------------------------------------                                                                                                                                                                                                                                                                                       |
| `name`              | `str`                                                       | **required**                                                                                                                                                                                                                                                                                                         | The human-readable name of the package. May contain a maximum of 200 characters.                                                                                                                                                                                                                                                               |
| `description`       | `str`                                                       | **required**                                                                                                                                                                                                                                                                                                         | A short free-form description of the package that will be shown in the PCM alongside the package name. May contain a maximum of 500 characters.                                                                                                                                                                                                |
| `description_full`  | `str` or `list` of `str`                                    | **required**                                                                                                                                                                                                                                                                                                         | A long free-form description of the package that will be shown in the PCM when the package is selected by the user. May include new lines. May contain a maximum of 5000 characters. If using list of strings, list will be joined to one string **without** adding any separators.                                                            |
| `identifier`        | `str`                                                       | **required**                                                                                                                                                                                                                                                                                                         | The unique identifier for the package.  May contain only alphanumeric characters and the dash (-) symbol. Must be between 2 and 50 characters in length. Must start with a latin character and end with a latin character or a numeral.                                                                                                        |
| `author`            | `dict` with `name` property and optional contact properties | first `author` from `project.authors` (**must** contain `name`).<br/>This option is **required** so plugin will fail if default missing.                                                                                                                                                                             | Object containing one mandatory field, `name`, containing the name of the package creator. An optional `contact` field may be present, for example: `author={ name="Foo", "Website"="https://bar.com" }` or `author={ name="Foo", email="bar@com" }`. Multiple contact fields **are** allowed.                                                 |
| `maintainer`        | same as `author`                                            | first `maintainer` from `project.maintainers` or `None` if does not contain `name` property                                                                                                                                                                                                                          | Same as `author` but not mandatory. If `project.maintainers` fallback fails (due to missing `name` for example), `maintainer` will be not included in final `metadata.json`                                                                                                                                                                    |
| `license`           | `str`                                                       | `license` from `project` metadata if it has [`text`](https://packaging.python.org/en/latest/specifications/declaring-project-metadata/#license) key (for example `license = {text = "MIT"}`).<br/>License with `file` key **not supported**.<br/>This option is **required** so plugin will fail if default missing. | A string containing the license under which the package is distributed. KiCad team requires opens-source license in order to be included in official KiCad's package repository. List of the supported licenses can be found [here](https://github.com/adamws/hatch-kicad/blob/master/src/hatch_kicad/licenses/supported.py).                  |
| `resources`         | `dict`                                                      | `project.urls` or `{}` if missing                                                                                                                                                                                                                                                                                    | Additional resource links for the package. Place your website, github, documentation and other links here.                                                                                                                                                                                                                                     |
| `status`            | `str`                                                       | **required**                                                                                                                                                                                                                                                                                                         | A string containing one of the following: `stable` - this package is stable for general use, `testing` - this package is in a testing phase, users should be cautious and report issues, `development` - this package is in a development phase and should not be expected to work fully, `deprecated` - this package is no longer maintained. |
| `kicad_version`     | `str`                                                       | **required**                                                                                                                                                                                                                                                                                                         | The minimum required KiCad version for this package.                                                                                                                                                                                                                                                                                           |
| `kicad_version_max` | `str`                                                       | `""`                                                                                                                                                                                                                                                                                                                 | The last KiCad version this package is compatible with.                                                                                                                                                                                                                                                                                        |
| `tags`              | `list` of `str`                                             | `[]`                                                                                                                                                                                                                                                                                                                 | The list of tags                                                                                                                                                                                                                                                                                                                               |
| `icon`              | `str`                                                       | **required**                                                                                                                                                                                                                                                                                                         | The path to the 64x64-pixel icon that will de displayed alongside the package in the KiCad's package dialog. Icon file **must** exist.                                                                                                                                                                                                         |

For more details see [kicad documentation](https://dev-docs.kicad.org/en/addons/).

> [!WARNING]
> Package `version` value is derived from **required** `project.version` field.
> KiCad version requirement is not compatible with [PEP-0440](https://peps.python.org/pep-0440/) so some
> valid python values won't pass PCM validation check. In such cases
> `kicad-package` plugin uses only [`base version`](https://packaging.pypa.io/en/stable/version.html#packaging.version.Version.base_version) value.

### How to run

To start build process, run `hatch build -t kicad-package`. If build successful, calculated `download_sha256`, `download_size` and `install_size` fields should be printed:

``` shell
$ hatch build --target kicad-package
[kicad-package]
Running custom, version: standard
package details:
{
  "download_sha256": "52cc67f37fcb272ac20ee5d8d50b214143e989c56a573bb49cc16a997d2dc701",
  "download_size": 33295,
  "install_size": 106682
}
dist/plugin-0.7.zip
```

By default, output artifacts are located at `dist` directory. There should be two files: `<package>.zip` and `metadata.json`.
For details how to use these files to submit package to KiCad addon repository see [this guide](https://dev-docs.kicad.org/en/addons/).

> [!WARNING]
> Package `download_url` is not set in produced `metadata.json` file.
> It needs to be manually updated before submitting to KiCad's PCM

## License

`hatch-kicad` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
