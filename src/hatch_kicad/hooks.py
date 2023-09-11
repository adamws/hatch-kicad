# SPDX-FileCopyrightText: 2023-present adamws <adamws@users.noreply.github.com>
#
# SPDX-License-Identifier: MIT
from hatchling.plugin import hookimpl

from hatch_kicad.build import KicadBuilder
from hatch_kicad.repository import KicadRepositoryHook


@hookimpl
def hatch_register_builder():
    return KicadBuilder


@hookimpl
def hatch_register_build_hook():
    return KicadRepositoryHook
