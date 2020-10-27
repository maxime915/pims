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
