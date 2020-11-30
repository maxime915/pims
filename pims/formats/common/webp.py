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
from pims.formats.utils.dict_utils import get_first
from pims.formats.utils.exiftool import read_raw_metadata
from pims.formats.utils.metadata import ImageMetadata, parse_float, parse_datetime, ImageChannel

from PIL import Image as PILImage

import numpy as np
from tifffile import lazyattr

log = logging.getLogger("pims.formats")


class WebPFormat(AbstractFormat):
    """WebP Format. Also supports WebP sequences.

    References
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp
        https://exiftool.org/TagNames/RIFF.html
    """

    @classmethod
    def init(cls):
        # https://github.com/python-pillow/Pillow/issues/5036
        from PIL import WebPImagePlugin
        assert WebPImagePlugin

    def __init__(self, path, **kwargs):
        super().__init__(path)
        self._pil = PILImage.open(path, formats=['WEBP'])

    def init_standard_metadata(self):
        imd = ImageMetadata()
        imd.width = self._pil.width
        imd.height = self._pil.height
        imd.depth = 1
        # n_frames not always present
        imd.duration = getattr(self._pil, "n_frames", 1)
        imd.significant_bits = 8
        imd.pixel_type = np.dtype("uint8")

        mode = self._pil.mode  # Possible values: RGB, RGBA
        if mode in ("RGB", "RGBA"):
            imd.n_channels = len(mode)
            for i, name in enumerate(mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#webp
            log.error("{}: Mode {} is not supported.".format(self._path, mode))
            raise MetadataParsingProblem(self._path)
        self._imd = imd

    @lazyattr
    def webp_raw_metadata(self):
        return read_raw_metadata(self._path)

    def init_complete_metadata(self):
        # Tags reference: https://exiftool.org/TagNames/RIFF.html
        imd = self._imd

        raw = self.webp_raw_metadata
        imd.description = get_first(raw, ("RIFF.Comment", "EXIF.ImageDescription", "EXIF.UserComment"))
        imd.acquisition_datetime = parse_datetime(get_first(raw, ("RIFF.DateTimeOriginal",
                                                                  "EXIF.CreationDate", "EXIF.DateTimeOriginal",
                                                                  "EXIF.ModifyDate")))

        imd.physical_size_x = self.parse_physical_size(raw.get("EXIF.XResolution"), raw.get("EXIF.ResolutionUnit"))
        imd.physical_size_y = self.parse_physical_size(raw.get("EXIF.YResolution"), raw.get("EXIF.ResolutionUnit"))

        if imd.duration > 1:
            total_time = raw.get("RIFF.Duration")  # String such as "0.84 s" -> all sequence duration
            if total_time:
                frame_rate = imd.duration / UNIT_REGISTRY(total_time)
                imd.frame_rate = frame_rate.to("Hz")

        imd.is_complete = True

    @staticmethod
    def parse_physical_size(physical_size, unit):
        supported_units = ("meters", "inches", "cm")
        if physical_size is not None and parse_float(physical_size) is not None and unit in supported_units:
            return parse_float(physical_size) * UNIT_REGISTRY(unit)
        return None

    def get_raw_metadata(self):
        store = super(WebPFormat, self).get_raw_metadata()
        for key, value in self.webp_raw_metadata.items():
            store.set(key, value)

        return store

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, proxypath):
        buf = proxypath.get("signature", proxypath.path.signature)
        return (len(buf) > 13 and
                buf[0] == 0x52 and
                buf[1] == 0x49 and
                buf[2] == 0x46 and
                buf[3] == 0x46 and
                buf[8] == 0x57 and
                buf[9] == 0x45 and
                buf[10] == 0x42 and
                buf[11] == 0x50 and
                buf[12] == 0x56 and
                buf[13] == 0x50)
