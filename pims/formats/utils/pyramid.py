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

from pims.api.utils.models import TierIndexType
from pims.processing.region import TileRegion


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
    def average_factor(self):
        return sum(self.factor) / 2.0

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
        return ceil(self.height / self.tile_height)

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
        return TileRegion(self, tx, ty).clip(self.width, self.height)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, PyramidTier) \
               and o.width == self.width and o.height == self.height \
               and o.tile_width == self.tile_width and o.tile_height == self.tile_height


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
        return self.max_zoom - zoom if self.max_zoom > 0 else 0

    def level_to_zoom(self, level):
        return self.max_level - level if self.max_level > 0 else 0

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

    def get_tier_at(self, tier_idx, tier_type):
        if tier_type == TierIndexType.ZOOM:
            return self.get_tier_at_zoom(tier_idx)
        else:
            return self.get_tier_at_level(tier_idx)

    def __len__(self):
        return len(self._tiers)

    def __iter__(self):
        return iter(self._tiers)

    def most_appropriate_tier_for_downsample_factor(self, factor):
        if factor < self.base.average_factor:
            return self.base

        for i in range(1, self.n_levels):
            if factor < self.tiers[i].average_factor:
                return self.tiers[i - 1]

        return self.tiers[self.n_levels - 1]

    def most_appropriate_tier(self, region, out_size):
        """
        Get the best pyramid tier to get `region` at `out_size`.

        Parameters
        ----------
        region : Region
            Requested region
        out_size : (int, int)
            Output size (width, height)

        Returns
        -------
        PyramidTier
            The most appropriate pyramid tier for this downsampling.
        """
        width_scale = region.true_width / out_size[0]
        height_scale = region.true_height / out_size[1]
        factor = (width_scale + height_scale) / 2.0
        return self.most_appropriate_tier_for_downsample_factor(factor)

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Pyramid) \
               and o.n_levels == self.n_levels \
               and all([a == b for (a, b) in zip(o.tiers, self.tiers)])


def normalized_pyramid(width, height):
    """
    Build a normalized pyramid, with normalized tiles, i.e.
    * each pyramid tier is half the size of the previous one, rounded up.
    * each tile has width of 256 pixels, except for right-most tiles.
    * each tile has height of 256 pixels, except for bottom-most tiles.

    Parameters
    ----------
    width : int
        Pyramid base width
    height : int
        Pyramid base height

    Returns
    -------
    pyramid : Pyramid
        A normalized pyramid.
    """
    pyramid = Pyramid()
    w, h = width, height

    ts = 256
    pyramid.insert_tier(w, h, (ts, ts))
    while w > ts or h > ts:
        w = ceil(w / 2)
        h = ceil(h / 2)
        pyramid.insert_tier(w, h, (ts, ts))

    return pyramid
