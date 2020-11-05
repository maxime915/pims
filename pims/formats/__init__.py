import logging
from importlib import import_module
from inspect import isclass, isabstract
from pkgutil import iter_modules

from pims.formats.abstract import AbstractFormat

FORMAT_PLUGIN_PREFIX = 'pims_format_'

logger = logging.getLogger("pims.formats")


def _discover_format_plugins(existing=None):
    if not existing:
        existing = set()
    plugins = existing
    plugins += [name for _, name, _ in iter_modules()
                if name.startswith(FORMAT_PLUGIN_PREFIX)]
    return plugins


def _find_formats_in_module(mod):
    """
    Find all Format classes in a module.

    Parameters
    ----------
    mod: module
        The module to analyze

    Returns
    -------
    formats: list
        The format classes
    """
    invalid_submodules = ["pims.formats.abstract", "pims.formats.factories"]
    formats = list()
    for _, name, _ in iter_modules(mod.__path__):
        submodule_name = "{}.{}".format(mod.__name__, name)
        if submodule_name in invalid_submodules:
            continue

        for var in vars(import_module(submodule_name)).values():
            if isclass(var) and issubclass(var, AbstractFormat) and not isabstract(var):
                format = var
                formats.append(format)
                logger.info(" * {} - {} imported.".format(format.get_identifier(), format.get_name()))
    return formats


def _get_all_formats():
    """
    Find all Format classes in modules specified in FORMAT_PLUGINS.

    Returns
    -------
    formats: list
        The format classes
    """
    formats = list()
    for module_name in FORMAT_PLUGINS:
        logger.info("Importing formats from {} plugin...".format(module_name))
        formats.extend(_find_formats_in_module(import_module(module_name)))

    return formats


FORMAT_PLUGINS = _discover_format_plugins([__name__])
FORMATS = {f.get_identifier(): f for f in _get_all_formats()}
