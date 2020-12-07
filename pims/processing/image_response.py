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

from pims.formats.utils.vips import format_to_vips_suffix, dtype_to_vips_format

from pyvips import Image as VIPSImage, Size

from pims.processing.adapters import imglib_adapters


class ImageResponse:
    pass


class ThumbnailResponse(ImageResponse):
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
        thumb = imglib_adapters.get((type(thumb), VIPSImage))(thumb)

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


class AssociatedResponse(ImageResponse):
    def __init__(self, in_image, associated_key, out_width, out_height, out_format):
        self.in_image = in_image
        self.associated_key = associated_key
        self.out_width = out_width
        self.out_height = out_height
        self.out_format = out_format
        self.out_format_params = {'Q': 75}

    def process(self):
        if self.associated_key == 'macro':
            associated = self.in_image.macro(self.out_width, self.out_height)
        elif self.associated_key == 'label':
            associated = self.in_image.label(self.out_width, self.out_height)
        else:
            associated = self.in_image.thumbnail(self.out_width, self.out_height, precomputed=True)

        associated = imglib_adapters.get((type(associated), VIPSImage))(associated)

        if associated.width != self.out_width or associated.height != self.out_height:
            associated = associated.thumbnail_image(self.out_width, height=self.out_height, size=Size.FORCE)

        associated = associated.scaleimage()  # Rescale to 0-255
        return associated

    def get_processed_buffer(self):
        processed = self.process()
        if type(processed) == VIPSImage:
            suffix = format_to_vips_suffix[self.out_format]
            buffer = processed.write_to_buffer(suffix, **self.out_format_params)
        else:
            raise NotImplementedError

        return buffer