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

from pims.processing.operations import OutputProcessor, ResizeImgOp, GammaImgOp, LogImgOp, RescaleImgOp, CastImgOp


class ImageResponse:
    def __init__(self, in_image, out_width, out_height, out_format, channels, z_slices, timepoints,
                 c_reduction, z_reduction, t_reduction, **kwargs):
        self.in_image = in_image

        self.channels = channels
        self.z_slices = z_slices
        self.timepoints = timepoints
        self.c_reduction = c_reduction
        self.z_reduction = z_reduction
        self.t_reduction = t_reduction

        self.out_width = out_width
        self.out_height = out_height
        self.out_format = out_format
        self.out_format_params = {k.replace('out_format', ''): v
                                  for k, v in kwargs.items() if k.startswith('out_format_')}

    def process(self):
        pass

    def get_response_buffer(self):
        return OutputProcessor(self.out_format, **self.out_format_params)(self.process())


class AdjustedImageResponse(ImageResponse):

    def __init__(self, in_image, out_width, out_height, out_format, channels, z_slices, timepoints,
                 c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                 min_intensities, max_intensities, log, **kwargs):
        super().__init__(in_image, out_width, out_height, out_format, channels, z_slices, timepoints, c_reduction,
                         z_reduction, t_reduction, **kwargs)
        self.gammas = gammas
        self.filters = filters
        self.colormaps = colormaps
        self.min_intensities = min_intensities
        self.max_intensities = max_intensities
        self.log = log


class ThumbnailResponse(AdjustedImageResponse):
    def __init__(self, in_image, out_width, out_height, out_format, channels, z_slices, timepoints,
                 c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                 min_intensities, max_intensities, log, use_precomputed, **kwargs):
        super().__init__(in_image, out_width, out_height, out_format, channels, z_slices, timepoints,
                         c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                         min_intensities, max_intensities, log, **kwargs)
        self.use_precomputed = use_precomputed

    def process(self):
        c, z, t = self.channels, self.z_slices[0], self.timepoints[0]
        img = self.in_image.thumbnail(self.out_width, self.out_height, c=c, z=z, t=t, precomputed=self.use_precomputed)
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
        img = RescaleImgOp()(img)
        return img
