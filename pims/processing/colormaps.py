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

from importlib import import_module

from palettable.palette import Palette

COLORMAPS = {}

MODULES = [
    'palettable.colorbrewer.diverging',
    'palettable.colorbrewer.qualitative',
    'palettable.colorbrewer.sequential',
    'palettable.tableau',
    'palettable.wesanderson',
    'palettable.cubehelix',
    'palettable.matplotlib',
    'palettable.mycarta',
    'palettable.cmocean.diverging',
    'palettable.cmocean.sequential',
    'palettable.cartocolors.diverging',
    'palettable.cartocolors.qualitative',
    'palettable.cartocolors.sequential',
    'palettable.lightbartlein.diverging',
    'palettable.lightbartlein.sequential',
    'palettable.scientific.diverging',
    'palettable.scientific.sequential'
]


def find_palettes(mod):
    """
    Find all Palette instances in mod.
    """
    return {
        k: v for k, v in vars(mod).items()
        if isinstance(v, Palette) and not k.endswith('_r')}


for mod in MODULES:
    palettes = find_palettes(import_module(mod))
    COLORMAPS.update(palettes)
