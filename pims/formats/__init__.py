# * Copyright (c) 2020. Authors: see NOTICE file.
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.

import logging
from importlib import import_module
from inspect import isclass, isabstract
from pkgutil import iter_modules

from pims.formats.utils.abstract import AbstractFormat

FORMAT_PLUGIN_PREFIX = 'pims_format_'
NON_PLUGINS_MODULES = ["pims.formats.utils"]

logger = logging.getLogger("pims.formats")


def _discover_format_plugins():

    plugins = [name for _, name, _ in iter_modules(__path__, prefix="pims.formats.")
               if name not in NON_PLUGINS_MODULES]
    plugins += [name for _, name, _ in iter_modules()
                if name.startswith(FORMAT_PLUGIN_PREFIX)]

    logger.info("Format plugins: found {} plugin(s) ({})".format(len(plugins), ", ".join(plugins)))
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
    formats = list()
    for _, name, _ in iter_modules(mod.__path__):
        submodule_name = "{}.{}".format(mod.__name__, name)
        try:
            for var in vars(import_module(submodule_name)).values():
                if isclass(var) and issubclass(var, AbstractFormat) and not isabstract(var) \
                        and 'Abstract' not in var.__name__:
                    format = var
                    formats.append(format)
                    format.init()
                    logger.info(" * {} - {} imported.".format(format.get_identifier(), format.get_name()))
        except ImportError as e:
            logger.error("{} submodule cannot be checked for formats !".format(submodule_name), exc_info=e)
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


FORMAT_PLUGINS = _discover_format_plugins()
FORMATS = {f.get_identifier(): f for f in _get_all_formats()}
