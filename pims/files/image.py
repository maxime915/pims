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
        return self._format.get_image_metadata().width

    @property
    def physical_size_x(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().physical_size_x

    @property
    def height(self):
        return self._format.get_image_metadata().height

    @property
    def physical_size_y(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().physical_size_y

    @property
    def depth(self):
        return self._format.get_image_metadata().depth

    @property
    def physical_size_z(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().physical_size_z

    @property
    def duration(self):
        return self._format.get_image_metadata().duration

    @property
    def frame_rate(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().frame_rate

    @property
    def n_channels(self):
        return self._format.get_image_metadata().n_channels

    @property
    def pixel_type(self):
        return self._format.get_image_metadata().pixel_type

    @property
    def significant_bits(self):
        return self._format.get_image_metadata().significant_bits

    @property
    def acquisition_datetime(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().acquisition_datetime

    @property
    def description(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().description

    @property
    def channels(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().channels

    @property
    def objective(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().objective

    @property
    def microscope(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().microscope

    @property
    def associated(self):
        self._format.require_complete_metadata()
        return self._format.get_image_metadata().associated

    @property
    def raw_metadata(self):
        return self._format.get_raw_metadata()
