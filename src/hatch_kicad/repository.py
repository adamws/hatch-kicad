# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import os
import shutil
from collections import ChainMap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TypedDict
from urllib.parse import urlparse, urlunparse

from hatchling.builders.hooks.plugin.interface import BuildHookInterface
from hatchling.utils.context import ContextStringFormatter

from hatch_kicad.utils import getsha256
from hatch_kicad.zip import ZipArchive

__all__ = ["KicadRepositoryHook"]


class DownloadableFileMetadata(TypedDict):
    url: str
    sha256: str
    update_time_utc: str
    update_timestamp: int


def get_file_metadata(filename: str, repository_url: str) -> DownloadableFileMetadata:
    mtime = os.path.getmtime(filename)
    dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
    return {
        "url": f"{repository_url}/{Path(filename).name}",
        "sha256": getsha256(filename),
        "update_time_utc": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "update_timestamp": int(mtime),
    }


def get_html_index_template() -> str:
    return """
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" href="data:," />
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/@picocss/pico@1/css/pico.min.css"
    />
  </head>
  <script src="https://cdn.jsdelivr.net/npm/linkifyjs@4.1.1/dist/linkify.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/linkify-html@4.1.1/dist/linkify-html.min.js"></script>
  <script>
    window.onload = function () {{
      let packages = document.getElementById("packages");
      packages.innerHTML = linkifyHtml(packages.innerHTML);
    }};
  </script>
  <body>
    <main class="container">
      <p>
        Add <mark>{repository_url}/repository.json</mark> to KiCad's repository
        list to use these packages:
      </p>
      <pre><code id="packages">{metadata_str}</code></pre>
      <footer>
        <small
          >Built with
          <a href="https://github.com/adamws/hatch-kicad" class="secondary"
            >hatch-kicad</a
          ></small
        >
      </footer>
    </main>
  </body>
</html>
"""


class KicadRepositoryHook(BuildHookInterface):
    PLUGIN_NAME = "kicad-repository"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.repo_directory = f"{self.directory}/repository"
        self.packages_out = f"{self.repo_directory}/packages.json"
        self.resources_out = f"{self.repo_directory}/resources.zip"
        self.__repository_url: str | None = None
        self.__html_data: str | None = None

    @property
    def repository_url(self) -> str:
        if not self.__repository_url:
            if "repository_url" in self.config:
                repository_url = self.config["repository_url"]
                if not isinstance(repository_url, str):
                    msg = (
                        "Option `repository_url` for build hook "
                        f"`{self.PLUGIN_NAME}` must be a string"
                    )
                    raise TypeError(msg)
            elif self.build_config and (download_url := self.build_config.download_url):
                parsed_download_url = urlparse(download_url)
                repository_url = urlunparse(
                    parsed_download_url._replace(
                        path="/".join(parsed_download_url.path.split("/")[:-1])
                    )
                )
                repository_url = str(repository_url)
            else:
                msg = (
                    "Option `repository_url` for build hook "
                    f"`{self.PLUGIN_NAME}` not found and unable to use "
                    f"`{self.build_config._BASE}.download_url` value to "
                    "determine default"
                )  # todo update message
                raise ValueError(msg)
            self.__repository_url = repository_url
        return self.__repository_url

    @property
    def html_data(self) -> str:
        if not self.__html_data:
            if "html_data" in self.config:
                html_data_template = self.config["html_data"]
                if not isinstance(html_data_template, str):
                    msg = (
                        "Option `html_data` for build hook "
                        f"`{self.PLUGIN_NAME}` must be a string"
                    )
                    raise TypeError(msg)

                with open(html_data_template) as f:
                    html_data_template = f.read()
            else:
                # use default
                html_data_template = get_html_index_template()

            formatter = ContextStringFormatter(
                ChainMap(
                    {
                        "metadata_str": lambda *args: json.dumps(
                            self.packages, indent=4
                        ),
                        "repository_url": lambda *args: self.repository_url,
                    },
                )
            )
            self.__html_data = formatter.format(html_data_template)
        return self.__html_data

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        pass

    def create_packages_file(self) -> None:
        with open(f"{self.directory}/metadata.json") as f:
            self.packages = {"packages": [json.load(f)]}
        with open(self.packages_out, "w", encoding="utf-8") as f:
            json.dump(self.packages, f, indent=4)

    def create_resources_file(self) -> None:
        with ZipArchive(
            self.resources_out,
            reproducible=self.build_config.reproducible,
        ) as zipf:
            zipf.write(
                self.build_config.icon, f"{self.build_config.identifier}/icon.png"
            )

    def create_repository_file(self) -> None:
        repository = {
            "$schema": "https://gitlab.com/kicad/code/kicad/-/raw/master/kicad/pcm/schemas/pcm.v1.schema.json#/definitions/Repository",
            "maintainer": self.build_config.author,
            "name": f"{self.repository_url} repository",
            "packages": get_file_metadata(self.packages_out, self.repository_url),
            "resources": get_file_metadata(self.resources_out, self.repository_url),
        }
        with open(f"{self.repo_directory}/repository.json", "w", encoding="utf-8") as f:
            json.dump(repository, f, indent=4)

    def create_index_html(self) -> None:
        if self.html_data:
            with open(f"{self.repo_directory}/index.html", "w") as f:
                f.write(self.html_data)

    def finalize(
        self, version: str, build_data: dict[str, Any], artifact_path: str
    ) -> None:
        shutil.rmtree(self.repo_directory, ignore_errors=True)
        os.makedirs(self.repo_directory)
        shutil.copy(artifact_path, self.repo_directory)

        self.create_packages_file()
        self.create_resources_file()
        self.create_repository_file()
        self.create_index_html()
