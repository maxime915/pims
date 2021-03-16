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


class Region:
    def __init__(self, top, left, width, height):
        self.top = top
        self.left = left
        self.width = width
        self.height = height

    def asdict(self):
        return {
            'top': self.top,
            'left': self.left,
            'width': self.width,
            'height': self.height
        }

    @property
    def right(self):
        return self.left + self.width

    @property
    def bottom(self):
        return self.top + self.height

    @property
    def is_normalized(self):
        return all(0 <= i <= 1 for i in (self.top, self.left, self.width, self.height))

    def __eq__(self, other) -> bool:
        if isinstance(other, Region):
            return self.top == other.top and self.left == other.left and \
                   self.width == other.width and self.height == other.height

        return False

    def toint(self, width_scale=1, height_scale=1):
        return Region(
            top=math.floor(self.top * height_scale),
            left=math.floor(self.left * width_scale),
            width=math.ceil(self.width * width_scale),
            height=math.ceil(self.height * height_scale)
        )

    def __str__(self) -> str:
        return "Region (Top: {} / Bottom: {} / Left: {} / Right: {} / Width: {} / Height: {})".format(
            self.top, self.bottom, self.left, self.right, self.width,  self.height)


class TileRegion(Region):
    def __init__(self, tier, tx, ty):
        left = tx * tier.tile_width
        top = ty * tier.tile_height
        width = min(left + tier.tile_width, tier.width) - left
        height = min(top + tier.tile_height, tier.height) - top
        super().__init__(top, left, width, height)
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

    def toregion(self):
        return Region(self.top, self.left, self.width, self.height)
