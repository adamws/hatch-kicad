# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from hatchling.plugin.manager import PluginManager

from hatch_kicad.build import KicadBuilder
from hatch_kicad.repository import KicadRepositoryHook


def test_builder_hook():
    plugin_manager = PluginManager()
    assert plugin_manager.builder.get("kicad-package") is KicadBuilder


def test_repository_hook():
    plugin_manager = PluginManager()
    assert plugin_manager.build_hook.get("kicad-repository") is KicadRepositoryHook
