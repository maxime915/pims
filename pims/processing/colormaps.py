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

from abc import ABC, abstractmethod

import numpy as np
from matplotlib.cm import get_cmap

from pims.api.utils.models import ColormapType


class Colormap(ABC):
    def __init__(self, id, ctype):
        self.id = id
        self.ctype = ctype
        
    @property
    def identifier(self):
        return self.id.upper()
    
    @property
    def name(self):
        return self.id.replace('_', ' ').title()

    @abstractmethod
    def lut(self, size=256, bitdepth=8):
        pass

    def as_image(self, width, height, bitdepth=8):
        lut = self.lut(size=width, bitdepth=bitdepth)
        return np.tile(lut, (height, 1, 1))


class MatplotlibColormap(Colormap):
    def __init__(self, id, ctype):
        super().__init__(id, ctype)

        self._mpl_cmap = dict()
        self._init_cmap(256)

    def _init_cmap(self, size):
        # (Matplotlib already precomputes with N=256)
        mpl_size = size if size != 256 else None
        self._mpl_cmap[size] = get_cmap(self.id, mpl_size)
        self._mpl_cmap[size]._init()

    def lut(self, size=256, bitdepth=8):
        if size not in self._mpl_cmap:
            self._init_cmap(size)

        lut = self._mpl_cmap[size]._lut[:size, :3] * (2 ** bitdepth - 1)
        if bitdepth > 16:
            dtype = np.uint
        elif bitdepth > 8:
            dtype = np.uint16
        else:
            dtype = np.uint8
        return lut.astype(dtype)


class ColorColormap(Colormap):
    def __init__(self, color):
        super().__init__(str(color), ColormapType.SEQUENTIAL)
        self._color = color

    def lut(self, size=256, bitdepth=8):
        r, g, b = self._color.as_float_tuple(alpha=False)
        n_colors = 1 if r == g == b else 3
        colors = (r,) if n_colors == 1 else (r, g, b)

        lut = np.zeros((size, n_colors))
        x = [0, size - 1]
        xvals = np.arange(size)
        for i, color in enumerate(colors):
            y = [0, color]
            lut[:, i] = np.interp(xvals, x, y)

        lut = lut * (2 ** bitdepth - 1)
        if bitdepth > 16:
            dtype = np.uint
        elif bitdepth > 8:
            dtype = np.uint16
        else:
            dtype = np.uint8
        return lut.astype(dtype)


def combine_lut(lut_a, lut_b):
    if lut_a.ndim == 1:
        lut_a = lut_a[:, np.newaxis]
    return np.take_along_axis(lut_b, lut_a, axis=0)


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

COLORMAPS = {}

for ctype, cmaps in mpl_cmaps.items():
    for cmap in cmaps:
        COLORMAPS[cmap.upper()] = MatplotlibColormap(cmap, ctype=ctype)
