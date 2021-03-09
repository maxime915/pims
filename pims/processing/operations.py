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
import numpy as np

from pims.formats.utils.vips import format_to_vips_suffix, dtype_to_vips_format
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


class CastImgOp(ImageOp):
    def __init__(self, dtype):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.dtype = dtype

    def _vips_impl(self, img, *args, **kwargs):
        return img.cast(dtype_to_vips_format[str(self.dtype)])


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
    """
    Apply logarithmic scale on image.
    Formula: out = ln(1+ in) * max_per_channel / ln(1 + max_per_channel)

    References
    ----------
    * Icy Logarithmic 2D viewer plugin (http://icy.bioimageanalysis.org/plugin/logarithmic-2d-viewer/)
    """

    def __init__(self, in_image, do):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl
        self.in_image = in_image
        self.do = do

    def ratio(self):
        stats = self.in_image.channels_stats()
        max_per_channel = np.asarray([stats[i]["maximum"] for i in range(self.in_image.n_channels)])
        ratio = max_per_channel / np.log1p(max_per_channel)
        return ratio.flatten()

    def _vips_impl(self, img, *args, **kwargs):
        if not self.do:
            return img
        return img.linear([1], [1]).log().linear(list(self.ratio()), [0])

    def _numpy_impl(self, img, *args, **kwargs):
        if not self.do:
            return img
        return np.log1p(img) * self.ratio()


class RescaleImgOp(ImageOp):
    def __init__(self, in_image, min_intensities, max_intensities):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.in_image = in_image
        self.mins = min_intensities
        self.maxs = max_intensities

    def do(self):
        return len(self.mins + self.maxs) > 0

    def same_min(self):
        return len(set(self.mins)) == 1

    def same_max(self):
        return len(set(self.maxs)) == 1

    def same_minmax(self):
        return len(set(self.mins + self.maxs)) == 1

    def _vips_impl(self, img):
        # TODO
        if not self.do:
            return img

        if (self.same_minmax() and self.mins[0] == "AUTO_IMAGE" and self.in_image.significant_bits > 8) or \
                (self.same_minmax() and self.mins[0] == "STRETCH_IMAGE"):
            # Rescale to 0-255
            return img.scaleimage()

        return img


class GammaImgOp(ImageOp):
    def __init__(self, exponent):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.exponent = exponent

    def _vips_impl(self, img):
        return img.gamma(exponent=self.exponent) if self.exponent else img
