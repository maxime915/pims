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

from pims.formats.utils.abstract import AbstractFormat


class JPEGFormat(AbstractFormat):
    def read_basic_metadata(self):
        pass

    def read_complete_metadata(self):
        super(JPEGFormat, self).read_complete_metadata()

    @classmethod
    def is_spatial(cls):
        return True

    def match(self):
        buf = self._path.signature()
        return (len(buf) > 2 and
                buf[0] == 0xFF and
                buf[1] == 0xD8 and
                buf[2] == 0xFF)


class PNGFormat(AbstractFormat):
    def read_basic_metadata(self):
        pass

    def read_complete_metadata(self):
        pass

    def match(self):
        buf = self._path.signature()
        return (len(buf) > 3 and
                buf[0] == 0x89 and
                buf[1] == 0x50 and
                buf[2] == 0x4E and
                buf[3] == 0x47)


class WebPFormat(AbstractFormat):
    def read_basic_metadata(self):
        pass

    def read_complete_metadata(self):
        pass

    def match(self):
        buf = self._path.signature()
        return (len(buf) > 13 and
                buf[0] == 0x52 and
                buf[1] == 0x49 and
                buf[2] == 0x46 and
                buf[3] == 0x46 and
                buf[8] == 0x57 and
                buf[9] == 0x45 and
                buf[10] == 0x42 and
                buf[11] == 0x50 and
                buf[12] == 0x56 and
                buf[13] == 0x50)
