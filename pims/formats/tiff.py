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

from tifffile.tifffile import lazyattr, astype

from pims.app import UNIT_REGISTRY
from pims.formats import AbstractFormat
from pims.formats.utils.metadata import ImageChannel, ImageMetadata, parse_float
from tifffile import tifffile


def read_tifffile(path):
    try:
        tf = tifffile.TiffFile(path)
    except tifffile.TiffFileError:
        tf = None
    return tf


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


class SVSFormat(AbstractTiffFormat):
    @classmethod
    def match(cls, proxypath):
        if super().match(proxypath):
            tf = proxypath.get("tf", read_tifffile, proxypath.path.resolve())
            return tf.is_svs
        return False

    @lazyattr
    def svs_raw_metadata(self):
        """Return metatata from Aperio image description as dict.

        The Aperio image description format is unspecified. Expect failures.
        """
        description = self.baseline.description
        if not description.startswith('Aperio '):
            raise ValueError('invalid Aperio image description')
        result = {}
        lines = description.split('\n')
        key, value = lines[0].strip().rsplit(None, 1)  # 'Aperio Image Library'
        result[key.strip()] = value.strip()
        if len(lines) == 1:
            return result
        items = lines[1].split('|')
        result['Description'] = items[0].strip()  # TODO: parse this?
        for item in items[1:]:
            key, value = item.split(' = ')
            result[key.strip()] = astype(value.strip())
        return result

    def init_complete_metadata(self):
        baseline = self._tf.pages[0]
        imd = self._image_metadata

        svs_metadata = self.svs_raw_metadata
        imd.description = baseline.description
        imd.acquisition_datetime = self.parse_acquisition_date(
            svs_metadata.get("Date", None), svs_metadata.get("Time", None))

        imd.physical_size_x = self.parse_physical_size(svs_metadata.get("MPP", None))
        imd.physical_size_y = imd.physical_size_x
        imd.objective.nominal_magnification = svs_metadata.get("AppMag", None)

        series_names = [s.name.lower() for s in self._tf.series]
        imd.associated.has_thumb = "thumbnail" in series_names
        imd.associated.has_label = "label" in series_names
        imd.associated.has_macro = "macro" in series_names

        imd.is_complete = True

    @staticmethod
    def parse_physical_size(physical_size, unit=None):
        if physical_size is not None and parse_float(physical_size) is not None:
            return parse_float(physical_size) * UNIT_REGISTRY("micrometers")
        return None

    @staticmethod
    def parse_acquisition_date(date, time=None):
        """
        Date examples: 11/25/13 , 2013-12-05T12:49:03.69Z
        Time examples: 15:10:34
        """
        try:
            if date and time:
                return datetime.strptime("{} {}".format(date, time), "%m/%d/%y %H:%M:%S")
            elif date:
                return datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
            else:
                return None
        except ValueError:
            return None

    def get_raw_metadata(self):
        store = super(SVSFormat, self).get_raw_metadata()
        for key, value in self.svs_raw_metadata.items():
            key = key if key is not "" else "Info"
            store.set(key.replace(" ", ""), value, namespace="Aperio")

        return store
