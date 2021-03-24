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

from pims.formats import FORMATS
from pims.formats.utils.abstract import CachedPathData


class FormatFactory:
    def __init__(self, formats=FORMATS.values()):
        self.formats = formats

    def match(self, path):
        proxy = CachedPathData(path)
        for format in self.formats:
            if format.match(proxy):
                return format.from_proxy(proxy)

        return None


class SpatialReadableFormatFactory(FormatFactory):
    def __init__(self):
        formats = [f for f in FORMATS.values() if f.is_spatial()]  # and f.is_readable()]
        super(SpatialReadableFormatFactory, self).__init__(formats)


class SpectralReadableFormatFactory(FormatFactory):
    def __init__(self):
        formats = [f for f in FORMATS.values() if f.is_spectral()]  # and f.is_readable()]
        super(SpectralReadableFormatFactory, self).__init__(formats)
