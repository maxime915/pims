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
import logging

import numpy as np
import pyvips.enums
from pyvips import Image as VIPSImage, Size as VIPSSize
from pyvips.error import Error as VIPSError

from pims.api.exceptions import MetadataParsingProblem
from pims.api.utils.models import HistogramType
from pims.formats.utils.abstract import (
    AbstractConvertor, AbstractParser, AbstractReader,
    NullHistogramReader
)
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageChannel, ImageMetadata
from pims.formats.utils.vips import (
    dtype_to_bits, vips_format_to_dtype,
    vips_interpretation_to_mode
)
from pims.processing.adapters import vips_to_numpy

log = logging.getLogger("pims.formats")


def cached_vips_file(format):
    return format.get_cached('_vips', VIPSImage.new_from_file, str(format.path))


def get_vips_field(vips_image, field, default=None):
    try:
        return vips_image.get_value(field)
    except VIPSError:
        return default


class VipsParser(AbstractParser):
    ALLOWED_MODES = ('L', 'RGB')

    def parse_main_metadata(self):
        image = cached_vips_file(self.format)

        imd = ImageMetadata()
        imd.width = image.width
        imd.height = image.height
        imd.n_channels = image.bands
        imd.depth = 1
        imd.duration = 1
        imd.n_intrinsic_channels = 1
        imd.n_channels_per_read = image.bands

        imd.pixel_type = np.dtype(vips_format_to_dtype[image.format])
        imd.significant_bits = dtype_to_bits(imd.pixel_type)

        mode = vips_interpretation_to_mode.get(image.interpretation)
        if mode in self.ALLOWED_MODES:
            for i, name in enumerate(mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            log.error("{}: Mode {} is not supported.".format(self.format.path, mode))
            raise MetadataParsingProblem(self.format.path)

        return imd

    def parse_known_metadata(self):
        imd = super().parse_known_metadata()
        return imd

    def parse_raw_metadata(self):
        store = super().parse_raw_metadata()

        raw = read_raw_metadata(self.format.path)
        for key, value in raw.items():
            store.set(key, value)

        return store


class VipsReader(AbstractReader):
    @staticmethod
    def vips_filename_with_options(filename, **options):
        if len(options) > 0:
            opt_string = '[' + ','.join("{}={}".format(k, v) for (k, v) in options.items()) + ']'
            return filename + opt_string
        return filename

    def vips_thumbnail(self, width, height, **loader_options):
        filename = self.vips_filename_with_options(str(self.format.path), **loader_options)

        # Seems it has been fixed by https://github.com/libvips/libvips/pull/2120
        # image = cached_vips_file(self.format)
        # if image.interpretation in ("grey16", "rgb16"):
        #     # Related to https://github.com/libvips/libvips/issues/1941 ?
        #     return VIPSImage.thumbnail(filename, width, height=height,
        #                                size=VIPSSize.FORCE, linear=True) \
        #         .colourspace(image.interpretation)

        return VIPSImage.thumbnail(filename, width, height=height, size=VIPSSize.FORCE)

    def read_thumb(self, out_width, out_height, **other):
        im = self.vips_thumbnail(out_width, out_height)
        return im.flatten() if im.hasalpha() else im

    def read_window(self, region, out_width, out_height, **other):
        image = cached_vips_file(self.format)
        region = region.scale_to_tier(self.format.pyramid.base)
        im = image.crop(region.left, region.top, region.width, region.height)
        return im.flatten() if im.hasalpha() else im

    def read_tile(self, tile, **other):
        return self.read_window(tile, tile.width, tile.height)


class VipsHistogramReader(NullHistogramReader):
    def is_complete(self):
        image = cached_vips_file(self.format)
        return image.width <= 1024 and image.height <= 1024

    def vips_hist_image(self):
        if self.is_complete():
            return cached_vips_file(self.format)

        def _thumb(format):
            # Seems it has been fixed by https://github.com/libvips/libvips/pull/2120
            # image = cached_vips_file(format)
            # if image.interpretation in ("grey16", "rgb16"):
            #     return VIPSImage.thumbnail(str(format.path), 1024, linear=True)\
            #         .colourspace(image.interpretation)
            return VIPSImage.thumbnail(str(format.path), 1024)

        return self.format.get_cached('_vips_hist_image', _thumb, self.format)

    def type(self):
        if self.is_complete():
            return HistogramType.COMPLETE
        else:
            return HistogramType.FAST

    def image_bounds(self):
        image = self.vips_hist_image()
        vips_stats = image.stats()
        np_stats = vips_to_numpy(vips_stats).astype(np.int)
        return tuple(np_stats[0, 0:2, 0])

    def image_histogram(self):
        image = self.vips_hist_image()
        return np.sum(vips_to_numpy(image.hist_find()), axis=2).squeeze()

    def channels_bounds(self):
        image = self.vips_hist_image()
        vips_stats = image.stats()
        np_stats = vips_to_numpy(vips_stats).astype(np.int)
        return list(map(tuple, np_stats[1:, :2, 0]))

    def channel_bounds(self, c):
        image = self.vips_hist_image()
        vips_stats = image.stats()
        np_stats = vips_to_numpy(vips_stats).astype(np.int)
        return tuple(np_stats[c + 1, :2, 0])

    def channel_histogram(self, c):
        image = self.vips_hist_image()
        return vips_to_numpy(image.hist_find(band=c))[0, :, 0]

    def planes_bounds(self):
        return self.channels_bounds()

    def plane_bounds(self, c, z, t):
        return self.channel_bounds(c)

    def plane_histogram(self, c, z, t):
        return self.channel_histogram(c)


class VipsSpatialConvertor(AbstractConvertor):
    def vips_source(self):
        return cached_vips_file(self.source)

    def conversion_format(self):
        from pims.formats.common.tiff import PyrTiffFormat
        return PyrTiffFormat

    def convert(self, dest_path):
        source = self.vips_source()

        result = source.tiffsave(
            str(dest_path), pyramid=True, tile=True, tile_width=256, tile_height=256, bigtiff=True,
            properties=False, strip=True, depth=pyvips.enums.ForeignDzDepth.ONETILE,
            compression=pyvips.enums.ForeignTiffCompression.LZW,
            region_shrink=pyvips.enums.RegionShrink.MEAN
        )
        return not bool(result)
