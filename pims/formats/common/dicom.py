#  * Copyright (c) 2020-2021. Authors: see NOTICE file.
#  *
#  * Licensed under the Apache License, Version 2.0 (the "License");
#  * you may not use this file except in compliance with the License.
#  * You may obtain a copy of the License at
#  *
#  *      http://www.apache.org/licenses/LICENSE-2.0
#  *
#  * Unless required by applicable law or agreed to in writing, software
#  * distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.
import logging
from datetime import datetime
from functools import cached_property

from pims import UNIT_REGISTRY
from pims.formats.utils.abstract import AbstractFormat, AbstractParser, AbstractReader
from pims.formats.utils.checker import SignatureChecker
from pims.formats.utils.engines.vips import VipsHistogramReader, VipsSpatialConvertor
from pims.formats.utils.metadata import ImageChannel, ImageMetadata, parse_float
from pims.formats.utils.vips import np_dtype
from pydicom import dcmread

log = logging.getLogger("pims.formats")


def cached_dcmread(format):
    return format.get_cached('_dcmread', dcmread, format.path.resolve(), force=True)


class DicomChecker(SignatureChecker):
    OFFSET = 128

    @classmethod
    def match(cls, pathlike):
        buf = cls.get_signature(pathlike)
        return (len(buf) > cls.OFFSET + 4 and
                buf[cls.OFFSET] == 0x44 and
                buf[cls.OFFSET + 1] == 0x49 and
                buf[cls.OFFSET + 2] == 0x43 and
                buf[cls.OFFSET + 3] == 0x4D)


class DicomParser(AbstractParser):
    def parse_main_metadata(self):
        ds = cached_dcmread(self.format)

        imd = ImageMetadata()
        imd.width = ds.Columns
        imd.height = ds.Rows
        imd.depth = 1  # TODO
        imd.duration = 1  # TODO

        imd.n_channels = ds.SamplesPerPixel  # Only 1 or 3
        imd.n_intrinsic_channels = ds.SamplesPerPixel
        imd.n_channels_per_read = 1
        if imd.n_channels == 3:
            imd.set_channel(ImageChannel(index=0, suggested_name='R'))
            imd.set_channel(ImageChannel(index=1, suggested_name='G'))
            imd.set_channel(ImageChannel(index=2, suggested_name='B'))
        else:
            imd.set_channel(ImageChannel(index=0, suggested_name='L'))

        imd.significant_bits = ds.BitsAllocated
        imd.pixel_type = np_dtype(imd.significant_bits)
        return imd

    def parse_known_metadata(self):
        ds = cached_dcmread(self.format)
        imd = super().parse_known_metadata()

        imd.description = None  # TODO
        imd.acquisition_datetime = self.parse_acquisition_date(
            ds.get('AcquisitionDate'), ds.get('AcquisitionTime'))
        if imd.acquisition_datetime is None:
            imd.acquisition_datetime = self.parse_acquisition_date(
                ds.get('ContentDate'), ds.get('ContentTime')
            )
        pixel_spacing = ds.get('PixelSpacing')
        if pixel_spacing:
            imd.physical_size_x = self.parse_physical_size(pixel_spacing[0])
            imd.physical_size_y = self.parse_physical_size(pixel_spacing[1])
        imd.physical_size_z = self.parse_physical_size(ds.get('SpacingBetweenSlices'))

        imd.is_complete = True
        return imd

    @staticmethod
    def parse_acquisition_date(date, time=None):
        """
        Date examples: 20211105
        Time examples: 151034, 151034.123
        """
        try:
            if date and time:
                return datetime.strptime(f"{date} {time.split('.')[0]}", "%Y%m%d %H%M%S")
            elif date:
                return datetime.strptime(date, "%Y%m%d")
            else:
                return None
        except (ValueError, TypeError):
            return None

    def parse_raw_metadata(self):
        # TODO
        return super(DicomParser, self).parse_raw_metadata()

    @staticmethod
    def parse_physical_size(physical_size):
        if physical_size is not None and parse_float(physical_size) is not None:
            return parse_float(physical_size) * UNIT_REGISTRY("millimeter")
        return None


class DicomReader(AbstractReader):
    def read_thumb(self, out_width, out_height, precomputed=None, c=None, z=None, t=None):
        pass

    def read_window(self, region, out_width, out_height, c=None, z=None, t=None):
        pass

    def read_tile(self, tile, c=None, z=None, t=None):
        pass


class DicomFormat(AbstractFormat):
    """Dicom Format.

    References

    """
    checker_class = DicomChecker
    parser_class = DicomParser
    reader_class = DicomReader
    histogram_reader_class = VipsHistogramReader  # TODO
    convertor_class = VipsSpatialConvertor  # TODO

    def __init__(self, *args, **kwargs):
        super(DicomFormat, self).__init__(*args, **kwargs)
        self._enabled = True

    @classmethod
    def is_spatial(cls):
        return True

    @cached_property
    def need_conversion(self):
        imd = self.main_imd
        return not (imd.width < 1024 and imd.height < 1024)  # TODO

    @property
    def media_type(self):
        return "application/dicom"
