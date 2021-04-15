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
import logging

import numpy as np
from pyvips import Image as VIPSImage, Size as VIPSSize
from pyvips.error import Error as VIPSError

from pims.api.exceptions import MetadataParsingProblem
from pims.formats.utils.abstract import AbstractParser, AbstractReader, AbstractHistogramManager
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageMetadata, ImageChannel
from pims.formats.utils.vips import vips_format_to_dtype, dtype_to_bits, vips_interpretation_to_mode
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
        image = cached_vips_file(self.format)

        filename = self.vips_filename_with_options(str(self.format.path), **loader_options)
        if image.interpretation in ("grey16", "rgb16"):
            # Related to https://github.com/libvips/libvips/issues/1941 ?
            return VIPSImage.thumbnail(filename, width, height=height,
                                       size=VIPSSize.FORCE, linear=True) \
                .colourspace(image.interpretation)

        return VIPSImage.thumbnail(filename, width, height=height, size=VIPSSize.FORCE)

    def read_thumb(self, out_width, out_height, **other):
        return self.vips_thumbnail(out_width, out_height)

    def read_window(self, region, out_width, out_height, **other):
        image = cached_vips_file(self.format)

        if region.is_normalized:
            imd = self.format.main_imd
            region = region.toint(width_scale=imd.width, height_scale=imd.height)

        return image.crop(region.left, region.top, region.width, region.height)

    def read_tile(self, tile, **other):
        return self.read_window(tile, tile.width, tile.height)


class VipsHistogramManager(AbstractHistogramManager):
    def compute_channels_stats(self):
        image = cached_vips_file(self.format)

        # TODO: finish implementation of fast histogram and conform to API spec.
        if image.width > 1024 or image.height > 1024:
            if image.interpretation in ("grey16", "rgb16"):
                image = VIPSImage.thumbnail(str(self.format.path), 1024, linear=True)\
                    .colourspace(image.interpretation)
            else:
                image = VIPSImage.thumbnail(str(self.format.path), 1024)

        vips_stats = image.stats()
        np_stats = vips_to_numpy(vips_stats)
        stats = {
            channel: dict(minimum=np_stats[channel + 1, 0].item(), maximum=np_stats[channel + 1, 1].item())
            for channel in range(np_stats.shape[0] - 1)
        }
        return stats
