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
from pims.formats.common.tiff import AbstractTiffFormat, read_tifffile
from pims.formats.utils.metadata import parse_float
from pims.formats.utils.pyramid import Pyramid
from tifffile import lazyattr, astype


class NDPIFormat(AbstractTiffFormat):
    """
    Hamamatsu NDPI.
    References
        https://openslide.org/formats/hamamatsu/
        https://docs.openmicroscopy.org/bio-formats/6.5.1/formats/hamamatsu-ndpi.html

    """
    @classmethod
    def get_name(cls):
        return "Hamamatsu NDPI"

    @classmethod
    def match(cls, cached_path):
        if super().match(cached_path):
            tf = cached_path.get("tf", read_tifffile, cached_path.path.resolve())
            return tf.is_ndpi
        return False

    @lazyattr
    def ndpi_tags(self):
        tags = self.baseline.ndpi_tags
        comments = tags.get("Comments", None)
        if comments:
            # Comments tag (65449): ASCII key=value pairs (not always present)
            lines = comments.split('\n')
            for line in lines:
                key, value = line.split('=')
                tags[key.strip()] = astype(value.strip())
            del tags["Comments"]
        return tags

    def init_complete_metadata(self):
        super(NDPIFormat, self).init_complete_metadata()
        imd = self._imd

        # Magnification extracted by OpenSlide
        imd.objective.nominal_magnification = parse_float(self.ndpi_tags.get("Magnification", None))
        # Magnification extracted by BioFormats
        imd.objective.calibrated_magnification = parse_float(self.ndpi_tags.get("Objective.Lens.Magnificant", None))
        imd.microscope.model = self.ndpi_tags.get("Model", None)

        # NDPI series: Baseline, Macro, Map
        for serie in self._tf.series:
            name = serie.name.lower()
            if name == "macro":
                associated = imd.associated_macro
            else:
                continue
            page = serie[0]
            associated.width = page.imagewidth
            associated.height = page.imagelength
            associated.n_channels = page.samplesperpixel

        imd.is_complete = True

    def get_raw_metadata(self):
        store = super(NDPIFormat, self).get_raw_metadata()
        for key, value in self.ndpi_tags.items():
            key = key.replace(" ", "")
            if key not in ('McuStarts', '65439'):
                store.set(key, value, namespace="Hamamatsu")

        return store

    @lazyattr
    def macro_series(self):
        return next((s for s in self._tf.series if s.name.lower() == 'macro'), None)

    def read_macro(self, *args, **kwargs):
        if not self.macro_series:
            return None

        page = self.macro_series[0]
        return page.asarray()

    def compute_channels_stats(self):
        return []

