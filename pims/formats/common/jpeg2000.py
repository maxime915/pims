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
from functools import cached_property

from pyvips import Image as VIPSImage

from pims import UNIT_REGISTRY
from pims.formats import AbstractFormat
from pims.formats.utils.checker import SignatureChecker
from pims.formats.utils.engines.vips import VipsReader, VipsHistogramReader, VipsParser, VipsSpatialConvertor, \
    cached_vips_file
from pims.formats.utils.metadata import parse_datetime, parse_float
from pims.formats.utils.pyramid import Pyramid

log = logging.getLogger("pims.formats")


class JPEG2000Checker(SignatureChecker):
    @classmethod
    def match(cls, pathlike):
        buf = cls.get_signature(pathlike)
        return (len(buf) > 50
                and buf[0] == 0x00
                and buf[1] == 0x00
                and buf[2] == 0x00
                and buf[3] == 0x0C
                and buf[16:24] == b"ftypjp2 ") or \
               (len(buf) > 50
                and buf[0] == 0xFF
                and buf[1] == 0x4F
                and buf[2] == 0xFF
                and buf[3] == 0x51)


class JPEG2000Parser(VipsParser):
    @staticmethod
    def parse_physical_size(physical_size, unit):
        supported_units = ("meters", "inches", "cm")
        if physical_size is not None and parse_float(physical_size) is not None \
                and unit in supported_units:
            return parse_float(physical_size) * UNIT_REGISTRY(unit)
        return None

    def parse_known_metadata(self):
        # Tags reference: https://exiftool.org/TagNames/JPEG.html
        imd = super().parse_known_metadata()
        raw = self.format.raw_metadata

        desc_fields = ("File.Comment", "EXIF.ImageDescription", "EXIF.UserComment")
        imd.description = raw.get_first_value(desc_fields)

        date_fields = ("EXIF.CreationDate", "EXIF.DateTimeOriginal", "EXIF.ModifyDate")
        imd.acquisition_datetime = parse_datetime(raw.get_first_value(date_fields))

        imd.physical_size_x = self.parse_physical_size(
            raw.get_value("EXIF.XResolution"),
            raw.get_value("EXIF.ResolutionUnit")
        )
        imd.physical_size_y = self.parse_physical_size(
            raw.get_value("EXIF.YResolution"),
            raw.get_value("EXIF.ResolutionUnit")
        )
        if imd.physical_size_x is None and imd.physical_size_y is None:
            imd.physical_size_x = self.parse_physical_size(
                raw.get_value("JFIF.XResolution"),
                raw.get_value("JFIF.ResolutionUnit")
            )
            imd.physical_size_y = self.parse_physical_size(
                raw.get_value("JFIF.YResolution"),
                raw.get_value("JFIF.ResolutionUnit")
            )
        imd.is_complete = True
        return imd

    def parse_pyramid(self):
        imd = self.format.main_imd
        p = Pyramid()
        p.insert_tier(
            imd.width, imd.height, (imd.width, imd.height), page_index=0
        )

        image = cached_vips_file(self.format)
        n_tiers = int(image.get_value('n-pages'))
        w, h = imd.width, imd.height
        for i in range(1, n_tiers):
            w, h = round(w / 2), round(h / 2)
            p.insert_tier(w, h, (w, h), page_index=i)
            # TODO: find a way to get tile size
        return p


class JPEG2000Reader(VipsReader):
    # Thumbnail already uses shrink-on-load feature in default VipsReader
    # (i.e it loads the right pyramid level according the requested dimensions)

    def read_window(self, region, out_width, out_height, **other):
        tier = self.format.pyramid.most_appropriate_tier(region, (out_width, out_height))
        region = region.scale_to_tier(tier)

        page = tier.data.get('page_index')
        tiff_page = VIPSImage.jp2kload(str(self.format.path), page=page)
        return tiff_page.extract_area(region.left, region.top, region.width, region.height)

    def read_tile(self, tile, **other):
        tier = tile.tier
        page = tier.data.get('page_index')
        tiff_page = VIPSImage.jp2kload(str(self.format.path), page=page)

        # There is no direct access to underlying tiles in vips
        # But the following computation match vips implementation so that only the tile
        # that has to be read is read.
        # https://github.com/jcupitt/tilesrv/blob/master/tilesrv.c#L461
        # TODO: is direct tile access significantly faster ?
        return tiff_page.extract_area(tile.left, tile.top, tile.width, tile.height)


class JPEG2000Format(AbstractFormat):
    """JPEG2000 Format.

    References
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html#jpeg-2000
        https://exiftool.org/TagNames/JPEG.html
        https://jpeg.org/jpeg2000/index.html
        http://www.openjpeg.org/doxygen/annotated.html
        https://github.com/ome/bioformats/blob/develop/components/formats-bsd/src/loci/formats/in/JPEG2000Reader.java
        https://github.com/libvips/libvips/blob/master/libvips/foreign/jp2kload.c
    """
    checker_class = JPEG2000Checker
    parser_class = JPEG2000Parser
    reader_class = JPEG2000Reader
    histogram_reader_class = VipsHistogramReader
    convertor_class = VipsSpatialConvertor

    def __init__(self, *args, **kwargs):
        super(JPEG2000Format, self).__init__(*args, **kwargs)
        self._enabled = True

    @classmethod
    def is_spatial(cls):
        return True

    @cached_property
    def need_conversion(self):
        """
        TODO - WARNING
        It is expected that no conversion is needed, as JPEG2000 is pyramidal and tiled.
        However:
        - LUNG1.jp2 from Cytomine internal dataset is extremely slow to decode
        - LUNG1-converted.jp2 converted from LUNG1_pyr.tif using vips, is much faster
        and decode time is acceptable (while slower than in pyramidal tif).
        Vips command:
            vips jp2ksave LUNG1_pyr.tif LUNG1-converted.jp2 --subsample-mode off
        => Identify internal differences between file to establish a conversion need rule.
        """
        return False
