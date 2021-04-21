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
from PIL import Image as PILImage

from pims.api.exceptions import MetadataParsingProblem
from pims.formats.utils.abstract import AbstractParser, AbstractReader, AbstractHistogramManager
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageMetadata, ImageChannel
from pims.processing.region import Region

log = logging.getLogger("pims.formats")


def cached_pillow_file(format, pil_format_slug):
    slugs = [pil_format_slug] if pil_format_slug else None
    return format.get_cached('_pil', PILImage.open, format.path, formats=slugs)


class PillowParser(AbstractParser):
    FORMAT_SLUG = None

    def parse_main_metadata(self):
        image = cached_pillow_file(self.format, self.FORMAT_SLUG)

        imd = ImageMetadata()
        imd.width = image.width
        imd.height = image.height
        imd.depth = 1
        imd.duration = getattr(image, "n_frames", 1)

        mode = image.mode  # Possible values: 1, L, P, RGB
        imd.pixel_type = np.dtype("uint8")
        imd.significant_bits = 8 if mode != "1" else 1

        channel_mode = "L" if mode == "1" else mode
        if channel_mode in ("L", "RGB"):
            imd.n_channels = len(channel_mode)
            for i, name in enumerate(channel_mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#bmp
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


class SimplePillowReader(AbstractReader):
    FORMAT_SLUG = None

    def read_thumb(self, out_width, out_height, precomputed=None, c=None, z=None, t=None):
        image = cached_pillow_file(self.format, self.FORMAT_SLUG)

        # We do not use Pillow resize() method as resize will be better handled by vips in response generation.
        return self.read_window(Region(0, 0, image.width, image.height), out_width, out_height, c, z, t)

    def read_window(self, region, out_width, out_height, c=None, z=None, t=None):
        image = cached_pillow_file(self.format, self.FORMAT_SLUG)
        region = region.scale_to_tier(self.format.pyramid.base)
        return image.crop((region.left, region.top, region.right, region.bottom))

    def read_tile(self, tile, c=None, z=None, t=None):
        return self.read_window(tile, tile.width, tile.height, c, z, t)


class PillowHistogramManager(AbstractHistogramManager):
    FORMAT_SLUG = None

    def compute_channels_stats(self):
        image = cached_pillow_file(self.format, self.FORMAT_SLUG)

        stats = {
            channel: dict(minimum=extrema[0], maximum=extrema[1])
            for channel, extrema in enumerate(image.getextrema())
        }
        return stats
