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
from pims.formats.common.tiff import AbstractTiffFormat, read_tifffile
from pims.formats.utils.metadata import parse_float
from pims.formats.utils.pyramid import Pyramid
from tifffile import lazyattr, astype


class SVSFormat(AbstractTiffFormat):
    """
    Aperio SVS format.
    References:
        https://openslide.org/formats/aperio/
        https://docs.openmicroscopy.org/bio-formats/6.5.1/formats/aperio-svs-tiff.html
        https://github.com/ome/bioformats/blob/master/components/formats-gpl/src/loci/formats/in/SVSReader.java
        https://www.leicabiosystems.com/digital-pathology/manage/aperio-imagescope/
        https://github.com/openslide/openslide/blob/master/src/openslide-vendor-aperio.c
    """

    @classmethod
    def get_name(cls):
        return "Leica Aperio SVS"

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
        imd = self._imd

        svs_metadata = self.svs_raw_metadata
        imd.description = self.baseline.description
        imd.acquisition_datetime = self.parse_acquisition_date(
            svs_metadata.get("Date", None), svs_metadata.get("Time", None))

        imd.physical_size_x = self.parse_physical_size(svs_metadata.get("MPP", None))
        imd.physical_size_y = imd.physical_size_x
        imd.objective.nominal_magnification = parse_float(svs_metadata.get("AppMag", None))

        for serie in self._tf.series:
            name = serie.name.lower()
            if name == "thumbnail":
                associated = imd.associated_thumb
            elif name == "label":
                associated = imd.associated_label
            elif name == "macro":
                associated = imd.associated_macro
            else:
                continue
            page = serie[0]
            associated.width = page.imagewidth
            associated.height = page.imagelength
            associated.n_channels = page.samplesperpixel

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
            store.set(key.replace(" ", ""), value, namespace="Aperio")

        return store

    @lazyattr
    def thumbnail_series(self):
        return next((s for s in self._tf.series if s.name.lower() == 'thumbnail'), None)

    @lazyattr
    def label_series(self):
        return next((s for s in self._tf.series if s.name.lower() == 'label'), None)

    @lazyattr
    def macro_series(self):
        return next((s for s in self._tf.series if s.name.lower() == 'macro'), None)

    def read_thumbnail(self, out_width, out_height, precomputed, *args):
        if precomputed and self.thumbnail_series is not None:
            page = self.thumbnail_series[0]
            return page.asarray()
        return super(SVSFormat, self).read_thumbnail(out_width, out_height, precomputed, *args)

    def read_label(self, *args, **kwargs):
        if not self.label_series:
            return None

        page = self.label_series[0]
        return page.asarray()

    def read_macro(self, *args, **kwargs):
        if not self.macro_series:
            return None

        page = self.macro_series[0]
        return page.asarray()
