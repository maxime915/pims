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
from pims.app import UNIT_REGISTRY
from pims.formats import AbstractFormat
from pims.formats.utils.dict_utils import get_first
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageMetadata, ImageChannel, parse_datetime, parse_float
from tifffile import lazyattr

log = logging.getLogger("pims.formats")


class JPEGFormat(AbstractFormat):
    """JPEG Format.

    References
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg
        https://exiftool.org/TagNames/JPEG.html
        https://www.w3.org/Graphics/JPEG/

    """
    def __init__(self, path, **kwargs):
        super().__init__(path)
        self._pil = PILImage.open(path, formats=["JPEG"])

    def init_standard_metadata(self):
        imd = ImageMetadata()
        imd.width = self._pil.width
        imd.height = self._pil.height
        imd.depth = 1
        imd.duration = 1
        imd.pixel_type = np.dtype("uint8")
        imd.significant_bits = 8

        mode = self._pil.mode  # Possible values: L, RGB, CMYK
        if mode in ("L", "RGB", "CMYK"):
            imd.n_channels = len(mode)
            for i, name in enumerate(mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            log.error("{}: Mode {} is not supported.".format(self._path, mode))
            raise MetadataParsingProblem(self._path)
        self._image_metadata = imd

    @lazyattr
    def jpeg_raw_metadata(self):
        return read_raw_metadata(self._path)

    def init_complete_metadata(self):
        # Tags reference: https://exiftool.org/TagNames/JPEG.html
        imd = self._image_metadata

        raw = self.jpeg_raw_metadata
        imd.description = get_first(raw, ("File.Comment", "EXIF.ImageDescription", "EXIF.UserComment"))
        imd.acquisition_datetime = parse_datetime(get_first(raw, ("EXIF.CreationDate", "EXIF.DateTimeOriginal",
                                                                  "EXIF.ModifyDate")))

        imd.physical_size_x = self.parse_physical_size(raw.get("EXIF.XResolution"), raw.get("EXIF.ResolutionUnit"))
        imd.physical_size_y = self.parse_physical_size(raw.get("EXIF.YResolution"), raw.get("EXIF.ResolutionUnit"))
        if imd.physical_size_x is None and imd.physical_size_y is None:
            imd.physical_size_x = self.parse_physical_size(raw.get("JFIF.XResolution"), raw.get("JFIF.ResolutionUnit"))
            imd.physical_size_y = self.parse_physical_size(raw.get("JFIF.YResolution"), raw.get("JFIF.ResolutionUnit"))
        imd.is_complete = True

    @staticmethod
    def parse_physical_size(physical_size, unit):
        supported_units = ("meters", "inches", "cm")
        if physical_size is not None and parse_float(physical_size) is not None and unit in supported_units:
            return parse_float(physical_size) * UNIT_REGISTRY(unit)
        return None

    def get_raw_metadata(self):
        store = super(JPEGFormat, self).get_raw_metadata()
        for key, value in self.jpeg_raw_metadata.items():
            store.set(key, value)

        return store

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, proxypath):
        buf = proxypath.get("signature", proxypath.path.signature)
        return (len(buf) > 2 and
                buf[0] == 0xFF and
                buf[1] == 0xD8 and
                buf[2] == 0xFF)
