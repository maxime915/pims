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

from pims.api.exceptions import NoMatchingFormatProblem
from pims.files.file import Path


class Image(Path):
    def __init__(self, *pathsegments, factory=None):
        super().__init__(*pathsegments)

        _format = factory.match(self) if factory else None
        if _format is None:
            raise NoMatchingFormatProblem(self)
        else:
            self._format = _format

    @property
    def format(self):
        return self._format

    @property
    def width(self):
        return self._format.width

    @property
    def physical_size_x(self):
        return self._format.physical_size_x

    @property
    def height(self):
        return self._format.height

    @property
    def physical_size_y(self):
        return self._format.physical_size_y

    @property
    def depth(self):
        return self._format.depth

    @property
    def physical_size_z(self):
        return self._format.physical_size_z

    @property
    def duration(self):
        return self._format.duration

    @property
    def frame_rate(self):
        return self._format.frame_rate

    @property
    def n_channels(self):
        return self._format.n_channels

    @property
    def pixel_type(self):
        return self._format.pixel_type

    @property
    def significant_bits(self):
        return self._format.significant_bits

    @property
    def acquisition_datetime(self):
        return self._format.acquisition_datetime

    @property
    def description(self):
        return self._format.description

    @property
    def core(self):
        return self._format.core_metadata

    @property
    def objective(self):
        return self._format.objective_metadata

    @property
    def microscope(self):
        return self._format.microscope_metadata

    @property
    def associated(self):
        return self._format.associated_metadata

    @property
    def raw_metadata(self):
        return self._format.get_raw_metadata()
