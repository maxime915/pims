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
from functools import cached_property
from typing import Optional, Union

import numpy as np
import zarr
from zarr import Array, Group

from pims.formats.utils.abstract import AbstractFormat, CachedDataPath
from pims.formats.utils.checker import AbstractChecker
from pims.formats.utils.histogram import DefaultHistogramReader
from pims.formats.utils.parser import AbstractParser
from pims.formats.utils.reader import AbstractReader
from pims.formats.utils.structures.metadata import ImageChannel, ImageMetadata, MetadataStore
from pims.processing.adapters import RawImagePixels
from pims.processing.region import Region, Tile


def cached_zarr_file(format: AbstractFormat) -> Union[Group, Array]:
    return format.get_cached('_zarr', zarr.open, str(format.path))


class ZarrChecker(AbstractChecker):
    @classmethod
    def match(cls, pathlike: CachedDataPath) -> bool:
        try:
            if not pathlike.path.is_dir():
                return False

            z = zarr.open(str(pathlike.path))
            # There is apparently no way to check the path is really a zarr
            # Check that there is at least one zarr "member"

            # We need to add more restrictive constraints when the spec will be
            # more fixed.
            if len(z) > 0 and len(z.attrs) > 0 and 'multiscales' in z.attrs:
                return True
        except Exception as e:  # noqa
            return False


class ZarrParser(AbstractParser):
    def parse_main_metadata(self) -> ImageMetadata:
        z = cached_zarr_file(self.format)
        md = z.attrs['multiscales'][0]
        axes = md['axes']
        base_path = md['datasets'][0]['path']
        base_array = z[base_path]
        dimensions = dict(zip(axes, base_array.shape))

        imd = ImageMetadata()
        imd.width = dimensions.get('x')
        imd.height = dimensions.get('y')
        imd.depth = dimensions.get('z', 1)
        imd.duration = dimensions.get('t', 1)
        imd.n_channels = dimensions.get('c', 1)
        imd.n_intrinsic_channels = dimensions.get('c', 1)
        imd.n_channels_per_read = dimensions.get('c', 1)  # TODO

        imd.pixel_type = np.dtype("uint16")
        imd.significant_bits = 16

        for c in range(imd.n_channels):
            imd.set_channel(ImageChannel(c))

        return imd

    def parse_known_metadata(self) -> ImageMetadata:
        imd = super().parse_known_metadata()
        return imd

    def parse_raw_metadata(self) -> MetadataStore:
        store = super().parse_raw_metadata()
        return store


class ZarrReader(AbstractReader):
    def _array_slices(self, x_np_slice, y_np_slice, c_np_slice, z_np_slice, t_np_slice):
        np_slices = dict()
        np_slices['x'] = np.s_[:] if x_np_slice is None else x_np_slice
        np_slices['y'] = np.s_[:] if y_np_slice is None else y_np_slice
        np_slices['c'] = np.s_[:] if c_np_slice is None else c_np_slice
        np_slices['z'] = np.s_[:] if z_np_slice is None else z_np_slice
        np_slices['t'] = np.s_[:] if t_np_slice is None else t_np_slice

        z = cached_zarr_file(self.format)
        md = z.attrs['multiscales'][0]
        axes = md['axes']

        ordered_slices = tuple(np_slices[axis] for axis in axes)
        return ordered_slices

    def _pixel_array(self, x_np_slice, y_np_slice, c_np_slice, z_np_slice, t_np_slice):
        slices = self._array_slices(x_np_slice, y_np_slice, c_np_slice, z_np_slice, t_np_slice)
        z = cached_zarr_file(self.format)
        md = z.attrs['multiscales'][0]
        base_path = md['datasets'][0]['path']
        base_array = z[base_path]
        image = base_array.oindex[slices]
        image = np.moveaxis(image, 0, -1)
        return image

    def read_thumb(
        self, out_width: int, out_height: int, precomputed: bool = None,
        c: Optional[int] = None, z: Optional[int] = None, t: Optional[int] = None
    ) -> RawImagePixels:
        width = self.format.main_imd.width
        height = self.format.main_imd.height
        return self.read_window(
            Region(0, 0, width, height),
            out_width, out_height, c, z, t
        )

    def read_window(
        self, region: Region, out_width: int, out_height: int,
        c: Optional[int] = None, z: Optional[int] = None, t: Optional[int] = None
    ) -> RawImagePixels:
        region = region.scale_to_tier(self.format.pyramid.base)
        return self._pixel_array(
            np.s_[region.left:region.right],
            np.s_[region.top:region.bottom],
            c, z, t
        )

    def read_tile(
        self, tile: Tile, c: Optional[int] = None, z: Optional[int] = None,
        t: Optional[int] = None
    ) -> RawImagePixels:
        return self.read_window(tile, int(tile.width), int(tile.height), c, z, t)


class ZarrFormat(AbstractFormat):
    """
    Known limitations:
    """
    checker_class = ZarrChecker
    parser_class = ZarrParser
    reader_class = ZarrReader
    histogram_reader_class = DefaultHistogramReader

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enabled = True

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def is_spectral(cls) -> bool:
        return True

    @cached_property
    def need_conversion(self) -> bool:
        return False
