# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from hatchling.plugin.manager import PluginManager

from hatch_kicad.build import KicadBuilder


def test_hooks():
    plugin_manager = PluginManager()
    assert plugin_manager.builder.get("kicad-package") is KicadBuilder
