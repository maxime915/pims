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
import math

from pims.processing.utils import split_tuple


class Region:
    def __init__(self, top, left, width, height, downsample=1.0):
        self.top = top
        self.left = left
        self.width = width
        self.height = height

        self.width_downsample = split_tuple(downsample, 0)
        self.height_downsample = split_tuple(downsample, 1)

    @property
    def downsample(self):
        return (self.width_downsample + self.height_downsample) / 2.0

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def true_left(self):
        return self.left * self.width_downsample

    @property
    def true_top(self):
        return self.top * self.height_downsample

    @property
    def true_width(self):
        return self.width * self.width_downsample

    @property
    def true_height(self):
        return self.height * self.height_downsample

    def scale(self, downsample):
        width_downsample = split_tuple(downsample, 0)
        height_downsample = split_tuple(downsample, 1)

        width_scale = self.width_downsample / width_downsample
        height_scale = self.height_downsample / height_downsample

        return Region(
            top=self.top * height_scale,
            left=self.left * width_scale,
            width=self.width * width_scale,
            height=self.height * height_scale,
            downsample=downsample
        )

    def toint(self):
        return Region(
            top=math.floor(self.top),
            left=math.floor(self.left),
            width=math.ceil(self.width),
            height=math.ceil(self.height),
            downsample=self.downsample
        )

    def clip(self, width, height):
        return Region(
            top=max(0, self.top),
            left=max(0, self.left),
            width=min(self.left + self.width, width) - self.left,
            height=min(self.top + self.height, height) - self.top,
            downsample=self.downsample
        )

    def scale_to_tier(self, tier):
        return self.scale((tier.width_factor, tier.height_factor))\
            .toint()\
            .clip(tier.width, tier.height)

    def asdict(self):
        return {
            'top': self.top,
            'left': self.left,
            'width': self.width,
            'height': self.height
        }

    def __eq__(self, other) -> bool:
        if isinstance(other, Region):
            scaled = other.scale(self.downsample)
            return self.top == scaled.top and self.left == scaled.left and \
                   self.width == scaled.width and self.height == scaled.height

        return False

    def __repr__(self) -> str:
        return "Region @ downsample ({}/{}) " \
               "(Top: {} / Bottom: {} / Left: {} / Right: {} / Width: {} / Height: {})".format(
            self.width_downsample, self.height_downsample,
            self.top, self.bottom, self.left, self.right, self.width, self.height)


class TileRegion(Region):
    def __init__(self, tier, tx, ty):
        left = tx * tier.tile_width
        top = ty * tier.tile_height
        width = tier.tile_width
        height = tier.tile_height
        super().__init__(top, left, width, height, downsample=(tier.width_factor, tier.height_factor))
        self.tier = tier
        self.tx = tx
        self.ty = ty

    @property
    def zoom(self):
        return self.tier.zoom

    @property
    def level(self):
        return self.tier.level

    @property
    def ti(self):
        return self.tier.txty2ti(self.tx, self.ty)
