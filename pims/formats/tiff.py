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
import pint

from pims.formats import AbstractFormat
from pims.formats.utils.metadata import ImageChannel, ImageMetadata
from tifffile import tifffile

UNIT_REG = pint.UnitRegistry()


class PyramidalTiff(AbstractFormat):
    def __init__(self, path):
        super().__init__(path)
        self._tf = tifffile.TiffFile(self._path)

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, proxypath):
        buf = proxypath.get("signature", proxypath.path.signature)
        return (len(buf) > 3 and
                ((buf[0] == 0x49 and buf[1] == 0x49 and
                  buf[2] == 0x2A and buf[3] == 0x0) or
                 (buf[0] == 0x4D and buf[1] == 0x4D and
                  buf[2] == 0x0 and buf[3] == 0x2A)))

    def init_standard_metadata(self):
        page = self._tf.pages[0]
        imd = ImageMetadata()

        imd.width = page.imagewidth
        imd.height = page.imagelength
        imd.depth = page.imagedepth
        imd.duration = 1
        imd.pixel_type = page.dtype
        imd.significant_bits = page.bitspersample

        imd.n_channels = page.samplesperpixel
        if imd.n_channels == 3:
            imd.set_channel(ImageChannel(index=0, samples_per_pixel=imd.significant_bits, suggested_name='R'))
            imd.set_channel(ImageChannel(index=1, samples_per_pixel=imd.significant_bits, suggested_name='G'))
            imd.set_channel(ImageChannel(index=2, samples_per_pixel=imd.significant_bits, suggested_name='B'))
        else:
            imd.set_channel(ImageChannel(index=0, samples_per_pixel=imd.significant_bits, suggested_name='L'))

        self._image_metadata = imd

    def init_complete_metadata(self):
        page = self._tf.pages[0]
        imd = self._image_metadata

        imd.description = page.description
        imd.acquisition_datetime = page.tags[306] if 306 in page.tags else self._path.creation_datetime

        def _physical_size_as_quantity(res_tag, unit_tag):
            unit = page.tags[unit_tag] if unit_tag in page.tags else None
            resolution = page.tags[res_tag] if res_tag in page.tags else None
            if not unit or resolution is None:
                return None
            rational = resolution.value
            return rational[1] / rational[0] * UNIT_REG(unit.value.name.lower())

        imd.physical_size_x = _physical_size_as_quantity("XResolution", "ResolutionUnit").to("micrometers").m
        imd.physical_size_y = _physical_size_as_quantity("YResolution", "ResolutionUnit").to("micrometers").m
        imd.is_complete = True

