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
from math import ceil

from pims.processing.region import Region


class PyramidTier:
    def __init__(self, width, height, tile_size, pyramid, data=None):
        self.width = width
        self.height = height
        self.tile_width = tile_size[0] if type(tile_size) == tuple else tile_size
        self.tile_height = tile_size[1] if type(tile_size) == tuple else tile_size
        self.pyramid = pyramid
        self.data = data if type(data) is dict else dict()

    @property
    def n_pixels(self):
        return self.width * self.height

    @property
    def factor(self):
        if self.pyramid.base is None:
            return 1.0, 1.0
        else:
            return self.pyramid.base.width / self.width, self.pyramid.base.height / self.height

    @property
    def width_factor(self):
        return self.factor[0]

    @property
    def height_factor(self):
        return self.factor[1]

    @property
    def level(self):
        return self.pyramid.tiers.index(self)

    @property
    def zoom(self):
        return self.pyramid.level_to_zoom(self.level)

    @property
    def max_tx(self):
        return ceil(self.width / self.tile_width)

    @property
    def max_ty(self):
        return ceil(self.height / self.tile_width)

    @property
    def max_ti(self):
        return self.max_tx * self.max_ty

    def ti2txty(self, ti):
        # ti = ty * max_tx + tx
        return ti % self.max_tx, ti // self.max_tx

    def txty2ti(self, tx, ty):
        return ty * self.max_tx + tx

    def ti2region(self, ti):
        # ti = ty * max_tx + tx
        return self.txty2region(*self.ti2txty(ti))

    def txty2region(self, tx, ty):
        left = tx * self.tile_width
        top = ty * self.tile_height
        width = min(left + self.tile_width, self.width) - left
        height = min(top + self.tile_height, self.height) - top
        return Region(top, left, width, height)


class Pyramid:
    def __init__(self):
        self._tiers = []

    @property
    def n_levels(self):
        return len(self._tiers)

    @property
    def n_zooms(self):
        return len(self._tiers)

    @property
    def max_level(self):
        return self.n_levels - 1

    @property
    def max_zoom(self):
        return self.n_zooms - 1

    @property
    def tiers(self):
        return self._tiers

    @property
    def base(self):
        return self._tiers[0] if self.n_levels > 0 else None

    def zoom_to_level(self, zoom):
        return self.max_zoom - zoom if zoom > 0 else 0

    def level_to_zoom(self, level):
        return self.max_level - level if level > 0 else 0

    def insert_tier(self, width, height, tile_size, **tier_data):
        tier = PyramidTier(width, height, tile_size, pyramid=self, data=tier_data)
        idx = 0
        while idx < len(self._tiers) and tier.n_pixels < self._tiers[idx].n_pixels:
            idx += 1
        self._tiers.insert(idx, tier)

    def get_tier_at_level(self, level):
        return self._tiers[level]

    def get_tier_at_zoom(self, zoom):
        return self.get_tier_at_level(self.zoom_to_level(zoom))

    def __len__(self):
        return len(self._tiers)

    def __iter__(self):
        return iter(self._tiers)

    def most_appropriate_tier(self, width, height):
        """
        Get the highest pyramid tier with size larger than `width` x `height`.

        Parameters
        ----------
        width : int
            Minimum tier width
        height : int
            Minimum tier height

        Returns
        -------
        PyramidTier
            Highest pyramid tier whose size is larger than given lengths.
        """
        best = self._tiers[0]
        for tier in self._tiers:
            if tier.width >= width and tier.height >= height:
                best = tier
            else:
                break
        return best
