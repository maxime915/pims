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

MODES = {
    ("1", "1;I"): ("uint8", 1),
    ("L", "L"): ("uint8", 8),
    ("I", "I;16B"): ("uint16", 16),
    ("I", "I;32B"): ("uint32", 32),
    ("RGB", "RGB"): ("uint8", 8),
    ("CMYK", "CMYK"): ("uint8", 8)
}


class PPMFormat(AbstractFormat):
    """PPM Format. Only binary variant is supported (P4, P5, P6). ASCII variant is unsupported.

    References
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#ppm
        https://acme.com/software/pbmplus/
        https://github.com/ome/bioformats/blob/master/components/formats-bsd/src/loci/formats/in/PGMReader.java
        https://en.wikipedia.org/wiki/Netpbm#File_formats
    """

    @classmethod
    def init(cls):
        # https://github.com/python-pillow/Pillow/issues/5036
        from PIL import PpmImagePlugin
        assert PpmImagePlugin

    def __init__(self, path, **kwargs):
        super().__init__(path)
        self._pil = PILImage.open(path, formats=['PPM'])

    def init_standard_metadata(self):
        imd = ImageMetadata()
        imd.width = self._pil.width
        imd.height = self._pil.height
        imd.depth = 1
        imd.duration = 1

        mode = self._pil.mode  # Possible values: 1, L, RGB, CMYK
        raw_mode = self._pil.tile[0][3][0]  # Possible values: 1;I, L; I;16B, I;32B, RGB, CMYK
        try:
            dtype, n_bits = MODES[(mode, raw_mode)]
            imd.pixel_type = np.dtype(dtype)
            imd.significant_bits = n_bits
        except KeyError:
            log.error("{}: Unsupported mode/raw_mode combination: {}/{}".format(self._path, mode, raw_mode))
            raise MetadataParsingProblem(self._path)

        channel_mode = "L" if mode in ("1", "I") else mode
        if channel_mode in ("L", "RGB"):
            imd.n_channels = len(channel_mode)
            for i, name in enumerate(channel_mode):
                imd.set_channel(ImageChannel(index=i, suggested_name=name))
        else:
            # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#ppm
            log.error("{}: Mode {} is not supported.".format(self._path, mode))
            raise MetadataParsingProblem(self._path)
        self._imd = imd

    @lazyattr
    def ppm_raw_metadata(self):
        return read_raw_metadata(self._path)

    def init_complete_metadata(self):
        imd = self._imd

        raw = self.ppm_raw_metadata
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
        store = super(PPMFormat, self).get_raw_metadata()
        for key, value in self.ppm_raw_metadata.items():
            store.set(key, value)

        return store

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, cached_path):
        buf = cached_path.get("signature", cached_path.path.signature)
        return (len(buf) > 1 and
                buf[0] == 0x50 and
                buf[1] in (0x34, 0x35, 0x36))
