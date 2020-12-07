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

from pims.processing.operations import OutputProcessor, ResizeImgOp, GammaImgOp, LogImgOp, RescaleImgOp


class ImageResponse:
    def __init__(self, in_image, out_width, out_height, out_format, **kwargs):
        self.in_image = in_image
        self.out_width = out_width
        self.out_height = out_height
        self.out_format = out_format
        self.out_format_params = {k.replace('out_format', ''): v
                                  for k, v in kwargs.items() if k.startswith('out_format_')}

    def process(self):
        pass

    def get_response_buffer(self):
        return OutputProcessor(self.out_format, **self.out_format_params)(self.process())


class ThumbnailResponse(ImageResponse):
    def __init__(self, in_image, out_width, out_height, out_format, log, use_precomputed, gamma, **kwargs):
        super().__init__(in_image, out_width, out_height, out_format, **kwargs)
        self.log = log
        self.use_precomputed = use_precomputed
        self.gamma = gamma

    def process(self):
        img = self.in_image.thumbnail(self.out_width, self.out_height, precomputed=self.use_precomputed)
        img = ResizeImgOp(self.out_width, self.out_height)(img)
        img = GammaImgOp(self.gamma[0])(img)
        img = LogImgOp(self.log)(img)
        img = RescaleImgOp()(img)
        return img


class AssociatedResponse(ImageResponse):
    def __init__(self, in_image, associated_key, out_width, out_height, out_format, **kwargs):
        super().__init__(in_image, out_width, out_height, out_format, **kwargs)
        self.associated_key = associated_key

    def get_raw_img(self):
        if self.associated_key == 'macro':
            associated = self.in_image.macro(self.out_width, self.out_height)
        elif self.associated_key == 'label':
            associated = self.in_image.label(self.out_width, self.out_height)
        else:
            associated = self.in_image.thumbnail(self.out_width, self.out_height, precomputed=True)

        return associated

    def process(self):
        img = self.get_raw_img()
        img = ResizeImgOp(self.out_width, self.out_height)(img)
        return img
