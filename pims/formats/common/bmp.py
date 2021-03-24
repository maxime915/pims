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
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageMetadata, parse_float, ImageChannel

from PIL import Image as PILImage

import numpy as np
from tifffile import lazyattr

log = logging.getLogger("pims.formats")


class BMPFormat(AbstractFormat):
    """BMP Format.

    References
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#bmp
        https://exiftool.org/TagNames/BMP.html
    """

    @classmethod
    def init(cls):
        # https://github.com/python-pillow/Pillow/issues/5036
        from PIL import BmpImagePlugin
        assert BmpImagePlugin

    def __init__(self, path, **kwargs):
        super().__init__(path)
        self._pil = PILImage.open(path, formats=['BMP'])

    def init_standard_metadata(self):
        imd = ImageMetadata()
        imd.width = self._pil.width
        imd.height = self._pil.height
        imd.depth = 1
        imd.duration = 1
        imd.pixel_type = np.dtype("uint8")

        mode = self._pil.mode  # Possible values: 1, L, P, RGB
        imd.significant_bits = 8 if mode != "1" else 1

        channel_mode = "L" if mode == "1" else mode
        if channel_mode in ("L", "RGB"):
            imd.n_channels = len(channel_mode)
            for i, name in enumerate(channel_mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#bmp
            log.error("{}: Mode {} is not supported.".format(self._path, mode))
            raise MetadataParsingProblem(self._path)
        self._imd = imd

    @lazyattr
    def bmp_raw_metadata(self):
        return read_raw_metadata(self._path)

    def init_complete_metadata(self):
        # Tags reference: https://exiftool.org/TagNames/BMP.html
        imd = self._imd

        raw = self.bmp_raw_metadata
        imd.description = raw.get("File.Comment")
        imd.acquisition_datetime = self._path.creation_datetime

        imd.physical_size_x = self.parse_physical_size(raw.get("File.PixelsPerMeterX"))
        imd.physical_size_y = self.parse_physical_size(raw.get("File.PixelsPerMeterY"))
        imd.is_complete = True

    @staticmethod
    def parse_physical_size(physical_size):
        if physical_size is not None and parse_float(physical_size) not in (None, 0.0):
            return 1 / parse_float(physical_size) * UNIT_REGISTRY("meters")
        return None

    def get_raw_metadata(self):
        store = super(BMPFormat, self).get_raw_metadata()
        for key, value in self.bmp_raw_metadata.items():
            store.set(key, value)

        return store

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, cached_path):
        buf = cached_path.get_cached("signature", cached_path.path.signature)
        return (len(buf) > 1 and
                buf[0] == 0x42 and
                buf[1] == 0x4D)
