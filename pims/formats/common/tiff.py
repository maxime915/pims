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
from datetime import datetime

from pims.app import UNIT_REGISTRY
from pims.formats import AbstractFormat
from pims.formats.utils.metadata import ImageMetadata, ImageChannel
from tifffile import tifffile, lazyattr


class AbstractTiffFormat(AbstractFormat):
    def __init__(self, path, _tf=None):
        super().__init__(path)
        self._tf = _tf if _tf else tifffile.TiffFile(self._path.resolve())

    @classmethod
    def is_spatial(cls):
        return True

    @classmethod
    def match(cls, proxypath):
        tf = proxypath.get("tf", read_tifffile, proxypath.path.resolve())
        if not tf:
            return False
        return True

    @classmethod
    def from_proxy(cls, proxypath):
        return cls(path=proxypath.path, _tf=proxypath.tf)

    @lazyattr
    def baseline(self):
        return self._tf.pages[0]

    def init_standard_metadata(self):
        imd = ImageMetadata()
        imd.width = self.baseline.imagewidth
        imd.height = self.baseline.imagelength
        imd.depth = self.baseline.imagedepth
        imd.duration = 1
        imd.pixel_type = self.baseline.dtype
        imd.significant_bits = self.baseline.bitspersample
        imd.n_channels = self.baseline.samplesperpixel
        if imd.n_channels == 3:
            imd.set_channel(ImageChannel(index=0, samples_per_pixel=imd.significant_bits, suggested_name='R'))
            imd.set_channel(ImageChannel(index=1, samples_per_pixel=imd.significant_bits, suggested_name='G'))
            imd.set_channel(ImageChannel(index=2, samples_per_pixel=imd.significant_bits, suggested_name='B'))
        else:
            imd.set_channel(ImageChannel(index=0, samples_per_pixel=imd.significant_bits, suggested_name='L'))

        self._image_metadata = imd

    def init_complete_metadata(self):
        tags = self.baseline.tags

        imd = self._image_metadata
        imd.description = self.baseline.description

        acquisition_datetime = self.parse_acquisition_date(tags.get(306))
        imd.acquisition_datetime = acquisition_datetime if acquisition_datetime else self._path.creation_datetime

        imd.physical_size_x = self.parse_physical_size(tags.get("XResolution"), tags.get("ResolutionUnit"))
        imd.physical_size_y = self.parse_physical_size(tags.get("YResolution"), tags.get("ResolutionUnit"))
        imd.is_complete = True

    @staticmethod
    def parse_acquisition_date(date):
        """
        Parse a date(time) from a TiffTag to datetime.

        Parameters
        ----------
        date: str, datetime

        Returns
        -------
        datetime: datetime, None
        """
        if isinstance(date, datetime):
            return date
        elif isinstance(date, str) and (len(date) != 19 or date[16] != ':'):
            return None
        else:
            try:
                return datetime.strptime(date, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                return None

    @staticmethod
    def parse_physical_size(physical_size, unit=None):
        """
        Parse a physical size and its unit from a TiffTag to a Quantity.

        Parameters
        ----------
        physical_size: tuple, int
        unit: tifffile.RESUNIT

        Returns
        -------
        physical_size: Quantity
        """
        if not unit or physical_size is None:
            return None
        if type(physical_size) == tuple and len(physical_size) == 1:
            rational = (physical_size[0], 1)
        elif type(physical_size) != tuple:
            rational = (physical_size, 1)
        else:
            rational = physical_size
        return rational[1] / rational[0] * UNIT_REGISTRY(unit.name.lower())


def read_tifffile(path):
    try:
        tf = tifffile.TiffFile(path)
    except tifffile.TiffFileError:
        tf = None
    return tf