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

from pyvips import Image as VIPSImage, Size as VIPSSize

from pims.formats.utils.vips import format_to_vips_suffix
from pims.processing.adapters import imglib_adapters


class ImageOp:
    def __init__(self):
        self._impl = {}

    @property
    def implementations(self):
        return list(self._impl.keys())

    def __call__(self, img, *args, **kwargs):
        if type(img) not in self.implementations:
            img = imglib_adapters.get((type(img), self.implementations[0]))(img)

        return self._impl[type(img)](img, *args, **kwargs)


class OutputProcessor(ImageOp):
    def __init__(self, format, **format_params):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.format = format
        self.format_params = format_params

    def _vips_impl(self, img, *args, **kwargs):
        suffix = format_to_vips_suffix[self.format]
        params = self.format_params
        clean_params = {}
        if suffix == '.jpeg':
            clean_params['Q'] = params.get('quality', params.get('jpeg_quality', 75))
        elif suffix == '.png':
            clean_params['compression'] = params.get('compression', params.get('png_compression', 6))
        elif suffix == '.webp':
            clean_params['lossless'] = params.get('lossless', params.get('webp_lossless', False))

        return img.write_to_buffer(suffix, **clean_params)

    def _pil_impl(self, img, format, *args, **kwargs):
        pass


class ResizeImgOp(ImageOp):
    def __init__(self, width, height):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.width = width
        self.height = height

    def _vips_impl(self, img, *args, **kwargs):
        if img.width != self.width or img.height != self.height:
            img = img.thumbnail_image(self.width, height=self.height, size=VIPSSize.FORCE)
        return img


class LogImgOp(ImageOp):
    def __init__(self, do):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.do = do

    def _vips_impl(self, img, *args, **kwargs):
        return img.log() if self.do else img


class RescaleImgOp(ImageOp):
    def __init__(self):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl

    def _vips_impl(self, img):
        # TODO
        # Rescale to 0-255
        return img.scaleimage()


class GammaImgOp(ImageOp):
    def __init__(self, exponent):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.exponent = exponent

    def _vips_impl(self, img):
        return img.gamma(exponent=self.exponent) if self.exponent else img
