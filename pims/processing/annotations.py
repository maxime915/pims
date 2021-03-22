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
from collections.abc import MutableSequence
import numpy as np

from pims.processing.region import Region


def is_grayscale(red, green, blue):
    return red == green == blue


class Annotation:
    def __init__(self, geometry, fill_color=None, stroke_color=None, stroke_width=None):
        self.geometry = geometry
        self.fill_color = fill_color
        self.stroke_color = stroke_color
        self.stroke_width = stroke_width

    @property
    def is_fill_grayscale(self):
        return is_grayscale(*self.fill_color) if self.fill_color else True

    @property
    def is_stroke_grayscale(self):
        return is_grayscale(*self.stroke_color) if self.stroke_color else True

    @property
    def is_grayscale(self):
        return self.is_fill_grayscale and self.is_stroke_grayscale

    @property
    def bounds(self):
        """Returns a (minx, miny, maxx, maxy) tuple (float values) that bounds the object.
        Ported from Shapely.
        """
        return self.geometry.bounds

    @property
    def region(self):
        left, top, right, bottom = self.bounds
        return Region(top, left, right - left, bottom - top)

    def __eq__(self, other):
        return isinstance(other, Annotation) \
               and self.geometry.equals(other.geometry) \
               and self.fill_color == other.fill_color \
               and self.stroke_color == other.stroke_color \
               and self.stroke_width == other.stroke_width


class AnnotationList(MutableSequence):
    def __init__(self):
        self._data = []

    def insert(self, index, value):
        if not isinstance(value, Annotation):
            raise TypeError("Value of type {} not allowed in {}.".format(
                value.__class__.__name__, self.__class__.__name__))
        self._data.insert(index, value)

    def __len__(self):
        return len(self._data)

    def __getitem__(self, index):
        return self._data[index]

    def __setitem__(self, index, value):
        if not isinstance(value, Annotation):
            raise TypeError("Value of type {} not allowed in {}.".format(
                value.__class__.__name__, self.__class__.__name__))
        self._data[index] = value

    def __delitem__(self, index):
        del self._data[index]

    @property
    def is_fill_grayscale(self):
        return all(annot.is_fill_grayscale for annot in self._data)

    @property
    def is_stroke_grayscale(self):
        return all(annot.is_stroke_grayscale for annot in self._data)

    @property
    def is_grayscale(self):
        return all(annot.is_grayscale for annot in self._data)

    @property
    def bounds(self):
        """
        Returns a (minx, miny, maxx, maxy) tuple (float values)
        that bounds the whole collection.
        """
        bounds = np.asarray([annot.bounds for annot in self._data])
        mini = np.min(bounds, axis=0)
        maxi = np.max(bounds, axis=0)
        return mini[0], mini[1], maxi[2], maxi[3]

    @property
    def region(self):
        left, top, right, bottom = self.bounds
        return Region(top, left, right - left, bottom - top)


def annotation_crop_affine_matrix(annot_region, in_region, out_width, out_height):
    rx = out_width / in_region.width
    ry = out_height / in_region.height
    tx = -annot_region.left * rx + ((in_region.width - annot_region.width) / 2) * rx
    ty = -annot_region.top * ry + ((in_region.height - annot_region.height) / 2) * ry
    return [rx, 0, 0, ry, tx, ty]
