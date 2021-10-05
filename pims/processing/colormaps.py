#  * Copyright (c) 2020-2021. Authors: see NOTICE file.
#  *
#  * Licensed under the Apache License, Version 2.0 (the "License");
#  * you may not use this file except in compliance with the License.
#  * You may obtain a copy of the License at
#  *
#  *      http://www.apache.org/licenses/LICENSE-2.0
#  *
#  * Unless required by applicable law or agreed to in writing, software
#  * distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

from abc import ABC, abstractmethod

import numpy as np
from matplotlib.cm import get_cmap
from pydantic.color import COLORS_BY_NAME

from pims.api.utils.models import ColormapType
from pims.formats.utils.vips import np_dtype
from pims.processing.color import Color


class Colormap(ABC):
    def __init__(self, id, ctype, inverted=False):
        self.id = id
        self.ctype = ctype
        self.inverted = inverted

    @property
    def identifier(self):
        inv = "!" if self.inverted else ""
        return inv + self.id.upper()

    @property
    def name(self):
        inv = " (Inverted)" if self.inverted else ""
        return self.id.replace('_', ' ').title() + inv

    @abstractmethod
    def lut(self, size=256, bitdepth=8):
        pass

    def as_image(self, width, height, bitdepth=8):
        lut = self.lut(size=width, bitdepth=bitdepth)
        return np.tile(lut, (height, 1, 1))

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Colormap) and \
               o.identifier == self.identifier


class MatplotlibColormap(Colormap):
    def __init__(self, id, ctype, inverted=False):
        super().__init__(id, ctype, inverted)

        self._mpl_cmap = dict()
        self._init_cmap(256)

    def _init_cmap(self, size):
        # (Matplotlib already precomputes with N=256)
        mpl_size = size if size != 256 else None
        mpl_name = self.id + ("_r" if self.inverted else "")
        self._mpl_cmap[size] = get_cmap(mpl_name, mpl_size)
        self._mpl_cmap[size]._init()

    def lut(self, size=256, bitdepth=8):
        if size not in self._mpl_cmap:
            self._init_cmap(size)

        lut = self._mpl_cmap[size]._lut[:size, :3] * (2 ** bitdepth - 1)
        return lut.astype(np_dtype(bitdepth))


class ColorColormap(Colormap):
    def __init__(self, color, inverted=False):
        super().__init__(str(color), ColormapType.SEQUENTIAL, inverted)
        self._color = color

    @property
    def color(self):
        return self._color

    def lut(self, size=256, bitdepth=8):
        r, g, b = self._color.as_float_tuple(alpha=False)
        n_colors = 1 if r == g == b else 3
        colors = (r,) if n_colors == 1 else (r, g, b)

        lut = np.zeros((size, n_colors))
        x = [0, size - 1]
        xvals = np.arange(size)
        for i, color in enumerate(colors):
            if self.inverted:
                y = [color, 0]
            else:
                y = [0, color]
            lut[:, i] = np.interp(xvals, x, y)

        lut = lut * (2 ** bitdepth - 1)
        return lut.astype(np_dtype(bitdepth))


def combine_lut(lut_a, lut_b):
    if lut_a.ndim == 1:
        lut_a = lut_a[:, np.newaxis]
    return np.take_along_axis(lut_b, lut_a, axis=0)


def default_lut(size=256, bitdepth=8):
    return np.arange(size).reshape((size, 1, 1)).astype(np_dtype(bitdepth))


mpl_cmaps = dict()
mpl_cmaps[ColormapType.PERCEPTUAL_UNIFORM] = [
    'viridis', 'plasma', 'inferno', 'magma', 'cividis']
mpl_cmaps[ColormapType.SEQUENTIAL] = [
    'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
    'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
    'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
    'binary', 'gist_yarg', 'gist_gray', 'bone',
    'spring', 'summer', 'autumn', 'winter', 'cool', 'Wistia',
    'hot', 'afmhot', 'gist_heat', 'copper']
mpl_cmaps[ColormapType.DIVERGING] = [
    'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdBu',
    'RdYlBu', 'RdYlGn', 'Spectral', 'coolwarm', 'bwr', 'seismic']
mpl_cmaps[ColormapType.CYCLIC] = [
    'twilight', 'twilight_shifted', 'hsv']
mpl_cmaps[ColormapType.DIVERGING] = [
    'Pastel1', 'Pastel2', 'Paired', 'Accent',
    'Dark2', 'Set1', 'Set2', 'Set3',
    'tab10', 'tab20', 'tab20b', 'tab20c']
mpl_cmaps[ColormapType.MISCELLANEOUS] = [
    'flag', 'prism', 'ocean', 'gist_earth', 'terrain', 'gist_stern',
    'gnuplot', 'gnuplot2', 'CMRmap', 'cubehelix', 'brg',
    'gist_rainbow', 'rainbow', 'jet', 'turbo', 'nipy_spectral',
    'gist_ncar']

# Non-trivial colormaps
COLORMAPS = {}

for ctype, cmaps in mpl_cmaps.items():
    for cmap in cmaps:
        for inv in (False, True):
            colormap = MatplotlibColormap(cmap, ctype=ctype, inverted=inv)
            COLORMAPS[colormap.identifier] = colormap

# Pre-load colormaps for named colors
COLOR_COLORMAPS = {}

for name in COLORS_BY_NAME:
    for inv in (False, True):
        colormap = ColorColormap(Color(name), inverted=inv)
        COLOR_COLORMAPS[colormap.identifier] = colormap

# All pre-loaded colormaps
ALL_COLORMAPS = {**COLORMAPS, **COLOR_COLORMAPS}

# Default colormaps per channel index
DEFAULT_CHANNEL_COLORMAPS = {
    0: ALL_COLORMAPS['RED'],
    1: ALL_COLORMAPS['LIME'],
    2: ALL_COLORMAPS['BLUE'],
    3: ALL_COLORMAPS['CYAN'],
    4: ALL_COLORMAPS['MAGENTA'],
    5: ALL_COLORMAPS['YELLOW']
}

RGB_COLORMAPS = [
    ALL_COLORMAPS['RED'], ALL_COLORMAPS['LIME'], ALL_COLORMAPS['BLUE']
]


def is_rgb_colormapping(colormaps):
    return len(colormaps) == 3 and colormaps == RGB_COLORMAPS
