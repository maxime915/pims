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

from pims.api.exceptions import MetadataParsingProblem
from pims.app import UNIT_REGISTRY
from pims.formats import AbstractFormat
from pims.formats.utils.dict_utils import get_first, invert
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageMetadata, ImageChannel, parse_datetime, parse_float

from PIL import Image as PILImage
from pims.processing.adapters import vips_to_numpy
from pyvips import Image as VIPSImage, Size

import numpy as np
from tifffile import lazyattr

log = logging.getLogger("pims.formats")


class PNGFormat(AbstractFormat):
    """PNG Formats. Also supports APNG sequences.

    References
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#apng-sequences
        https://exiftool.org/TagNames/PNG.html
        http://www.libpng.org/pub/png/spec/
        https://github.com/ome/bioformats/blob/master/components/formats-bsd/src/loci/formats/in/APNGReader.java
    """

    def __init__(self, path, **kwargs):
        super().__init__(path)
        self._pil = PILImage.open(path, formats=["PNG"])
        self._vips = VIPSImage.new_from_file(str(path))

    def init_standard_metadata(self):
        imd = ImageMetadata()
        imd.width = self._pil.width
        imd.height = self._pil.height
        imd.depth = 1
        # n_frames not always present
        imd.duration = getattr(self._pil, "n_frames", 1)

        mode = self._pil.mode  # Possible values: 1, I, L, LA, RGB, RGBA, P
        print(self._pil.tile)
        if mode == '1':
            imd.significant_bits = 1
            imd.pixel_type = np.dtype("uint8")
        elif mode.startswith('I'):
            # Mode should be I;16 but in practice, I is returned.
            imd.significant_bits = 16
            imd.pixel_type = np.dtype("uint16")
        else:
            imd.significant_bits = 8
            imd.pixel_type = np.dtype("uint8")

        channel_mode = "L" if mode.startswith("I") or mode == "1" else mode
        if channel_mode in ("L", "RGB", "RGBA", "LA"):
            imd.n_channels = len(channel_mode)
            for i, name in enumerate(channel_mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            # Unsupported modes: P
            # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#png
            log.error("{}: Mode {} is not supported.".format(self._path, mode))
            raise MetadataParsingProblem(self._path)
        self._imd = imd

    @lazyattr
    def png_raw_metadata(self):
        return read_raw_metadata(self._path)

    def init_complete_metadata(self):
        # Tags reference: https://exiftool.org/TagNames/PNG.html
        imd = self._imd

        raw = self.png_raw_metadata
        imd.description = get_first(raw, ("PNG.Comment", "EXIF.ImageDescription", "EXIF.UserComment"))
        imd.acquisition_datetime = parse_datetime(get_first(raw, ("PNG.CreationTime", "PNG.ModifyDate",
                                                                  "EXIF.CreationDate", "EXIF.DateTimeOriginal",
                                                                  "EXIF.ModifyDate")))

        imd.physical_size_x = self.parse_physical_size(raw.get("PNG.PixelsPerUnitX"), raw.get(
            "PNG.PixelUnits"), True)
        imd.physical_size_y = self.parse_physical_size(raw.get("PNG.PixelsPerUnitY"), raw.get(
            "PNG.PixelUnits"), True)
        if imd.physical_size_x is None and imd.physical_size_y is None:
            imd.physical_size_x = self.parse_physical_size(raw.get("EXIF.XResolution"), raw.get(
                "EXIF.ResolutionUnit"), False)
            imd.physical_size_y = self.parse_physical_size(raw.get("EXIF.YResolution"), raw.get(
                "EXIF.ResolutionUnit"), False)

        if imd.duration > 1:
            duration = self._pil.info.get("duration")  # in milliseconds
            imd.frame_rate = 1 / duration / 1000 * UNIT_REGISTRY("Hz") if duration is not None else None

        imd.is_complete = True

    @staticmethod
    def parse_physical_size(physical_size, unit, inverse):
        supported_units = {1: "meter", 2: "inch"}
        if type(unit) == str:
            supported_units = {"meters": "meter", "inches": "inch"}
        if physical_size is not None and parse_float(physical_size) is not None \
                and unit in supported_units.keys():
            physical_size = parse_float(physical_size)
            if inverse:
                physical_size = 1 / physical_size
            return physical_size * UNIT_REGISTRY(supported_units[unit])
        return None

    def get_raw_metadata(self):
        store = super(PNGFormat, self).get_raw_metadata()
        for key, value in self.png_raw_metadata.items():
            store.set(key, value)

        return store

    def read_thumbnail(self, out_width, out_height, precomputed, c, z, t):
        t = t if t is not None else 0

        if t > 0:
            self._pil.seek(t)
            # https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.resize
            return self._pil.resize((out_width, out_height))  # Bicubic interpolation

        if self._imd.significant_bits == 16:
            # Related to https://github.com/libvips/libvips/issues/1941 ?
            return VIPSImage.thumbnail(str(self._path), out_width, height=out_height, size=Size.FORCE,
                                       linear=True).colourspace("grey16")
        return VIPSImage.thumbnail(str(self._path), out_width, height=out_height, size=Size.FORCE)

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, cached_path):
        buf = cached_path.get("signature", cached_path.path.signature)
        return (len(buf) > 3 and
                buf[0] == 0x89 and
                buf[1] == 0x50 and
                buf[2] == 0x4E and
                buf[3] == 0x47)

    def compute_channels_stats(self):
        vips_stats = self._vips.stats()
        np_stats = vips_to_numpy(vips_stats)
        stats = {
            channel: dict(minimum=np_stats[channel + 1, 0].item(), maximum=np_stats[channel + 1, 1].item())
            for channel in range(np_stats.shape[0] - 1)
        }
        self._channels_stats = stats
        return stats
