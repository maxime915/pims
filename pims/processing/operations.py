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
import logging

from pyvips import Image as VIPSImage, Size as VIPSSize
import numpy as np

from pims.formats.utils.vips import format_to_vips_suffix, dtype_to_vips_format
from pims.processing.adapters import imglib_adapters

log = logging.getLogger("pims.processing")


class ImageOp:
    """
    Base class that all image operations derive from.

    Image operations are expected to be called like a function: `MyImgOp(param)(img)`.
    """
    def __init__(self):
        self._impl = {}

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def parameters(self):
        return {k: v for (k,v) in self.__dict__.items() if not k.startswith("_")}

    @property
    def implementations(self):
        return list(self._impl.keys())

    def __call__(self, img, *args, **kwargs):
        log.info("Apply {} with parameters: {}".format(self.name, self.parameters))
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
    """Cast an image to another type.

    Attributes
    ----------
    dtype : data-type, optional
        Desired data-type for the image.
    """
    def __init__(self, dtype):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl
        self.dtype = dtype

    def _vips_impl(self, img, *args, **kwargs):
        return img.cast(dtype_to_vips_format[str(self.dtype)])

    def _numpy_impl(self, img, *args, **kwargs):
        return img.astype(self.dtype)


class ResizeImgOp(ImageOp):
    """Resize a 2D image to expected size.

    Attributes
    ----------
    width : int
        Expected width
    height: int
        Expected height
    """
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
    """Apply logarithmic scale on image.
    Image is expected to be a normalized float array.

    Formula: out = ln(1+ in) * max_per_channel / ln(1 + max_per_channel)

    Attributes
    ----------
    max_intensities : list of int
        Maximum intensity per channel in the original image

    References
    ----------
    * Icy Logarithmic 2D viewer plugin (http://icy.bioimageanalysis.org/plugin/logarithmic-2d-viewer/)
    """

    def __init__(self, max_intensities):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl
        self.max_intensities = max_intensities

    def ratio(self):
        ratio = self.max_intensities / np.log1p(self.max_intensities)
        return ratio.flatten()

    def _vips_impl(self, img, *args, **kwargs):
        return img.linear([1], [1]).log().linear(list(self.ratio()), [0])

    def _numpy_impl(self, img, *args, **kwargs):
        return np.log1p(img) * self.ratio()


class GammaImgOp(ImageOp):
    """Apply gamma on an image.
    Image is expected to be a normalized float array.

    Attributes
    ----------
    exponents : list of float
        Exponents to apply per channel
    """
    def __init__(self, exponents):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl
        self.exponents = exponents

    def _vips_impl(self, img):
        # TODO: apply gamma per channel (split with band join) if needed.
        # TODO: now first gamma is applied on all channels.
        # return img.math2_const("pow", self.exponent)
        exp = self.exponents[0]
        return img.gamma(exponent=1/exp)

    def _numpy_impl(self, img):
        return np.power(img, self.exponents)


class RescaleImgOp(ImageOp):
    """Rescale a normalized float array to maximum admissible value for a given bit depth.

    Attributes
    ----------
    bitdepth: int
        Exponent used to rescale values so that out = in * pow(2, bitdepth)
    """
    def __init__(self, bitdepth):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl
        self.bitdepth = bitdepth

    def factor(self):
        return 2 ** self.bitdepth

    def _vips_impl(self, img):
        return img.linear([self.factor()], [0])

    def _numpy_impl(self, img):
        return img * self.factor()


class NormalizeImgOp(ImageOp):
    """Normalize an image according min and max intensities per channel.

    Attributes
    ----------
    min_intensities : list of int
        Minimum intensities per channel
    max_intensities : list of int
        Maximum intensities per channel
    """
    def __init__(self, min_intensities, max_intensities):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl

        self.min_intensities = np.array(min_intensities)
        self.max_intensities = np.array(max_intensities)

    def invdiff(self):
        return 1. / (self.max_intensities - self.min_intensities)

    def _vips_impl(self, img):
        return img.linear(list(self.invdiff()), list(-self.min_intensities * self.invdiff()))

    def _numpy_impl(self, img):
        return (img - self.min_intensities) * self.invdiff()
