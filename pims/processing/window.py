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

from pims.formats.utils.vips import format_to_vips_suffix

from pyvips import Image as VIPSImage


class Thumbnail:
    def __init__(self, in_image, out_width, out_height, out_format, log, use_precomputed, gamma):
        self.in_image = in_image
        self.out_width = out_width
        self.out_height = out_height
        self.out_format = out_format
        self.out_format_params = {'Q': 75}
        self.log = log
        self.use_precomputed = use_precomputed
        self.gamma = gamma

    def process(self):
        thumb = self.in_image.thumbnail(self.out_width, self.out_height, precomputed=self.use_precomputed)
        if type(thumb) != VIPSImage:
            thumb = VIPSImage.new_from_array(thumb)

        if self.gamma:
            thumb = thumb.gamma(exponent=self.gamma[0])

        if self.log:
            thumb = thumb.log()

        thumb = thumb.scaleimage()  # Rescale to 0-255
        return thumb

    def get_processed_buffer(self):
        processed = self.process()
        if type(processed) == VIPSImage:
            suffix = format_to_vips_suffix[self.out_format]
            buffer = processed.write_to_buffer(suffix, **self.out_format_params)
        else:
            raise NotImplementedError

        return buffer
