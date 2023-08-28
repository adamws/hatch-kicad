from hatchling.plugin import hookimpl

from hatch_kicad.build import KicadBuilder


@hookimpl
def hatch_register_builder():
    return KicadBuilder
