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
import time

import pyvips
from pyvips import Image as VIPSImage, Size as VIPSSize
import numpy as np
from rasterio.features import rasterize
from shapely.affinity import affine_transform

from pims.api.utils.models import Colorspace
from pims.formats.utils.vips import format_to_vips_suffix, dtype_to_vips_format, vips_format_to_dtype
from pims.processing.adapters import imglib_adapters, numpy_to_vips
from pims.processing.annotations import ParsedAnnotations, contour, stretch_contour
from pims.processing.color import np_int2rgb
from pims.processing.utils import find_first_available_int

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
        return {k: v for (k, v) in self.__dict__.items() if not k.startswith("_")}

    @property
    def implementations(self):
        return list(self._impl.keys())

    @property
    def implementation_adapters(self):
        return imglib_adapters

    def __call__(self, obj, *args, **kwargs):
        start = time.time()

        if type(obj) not in self.implementations:
            obj = self.implementation_adapters.get((type(obj), self.implementations[0]))(obj)

        processed = self._impl[type(obj)](obj, *args, **kwargs)
        end = time.time()
        log.info("Apply {} in {}µs".format(self.name, round((end - start) / 1e-6, 3)))
        return processed


class OutputProcessor(ImageOp):
    def __init__(self, format, bitdepth, **format_params):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.format = format
        self.bitdepth = bitdepth
        self.format_params = format_params

    def expected_dtype(self):
        if self.bitdepth <= 8:
            return 'uint8'
        elif self.bitdepth <= 16:
            return 'uint16'
        else:
            return 'uint8'

    def _vips_impl(self, img, *args, **kwargs):
        suffix = format_to_vips_suffix[self.format]
        params = self.format_params
        clean_params = {}
        if suffix == '.jpg':
            clean_params['Q'] = params.get('quality', params.get('jpeg_quality', 75))
            clean_params['strip'] = True
        elif suffix == '.png':
            clean_params['compression'] = params.get('compression', params.get('png_compression', 6))
        elif suffix == '.webp':
            clean_params['lossless'] = params.get('lossless', params.get('webp_lossless', False))
            clean_params['strip'] = True
            clean_params['Q'] = params.get('quality', params.get('webp_quality', 75))

        # Clip by casting image
        img = img.cast(dtype_to_vips_format[self.expected_dtype()])

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

            if img.interpretation in ("grey16", "rgb16"):
                # Related to https://github.com/libvips/libvips/issues/1941 ?
                return img.thumbnail_image(self.width, height=self.height, size=VIPSSize.FORCE, linear=True) \
                    .colourspace(img.interpretation)

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
        ratio = 1. / np.log1p(1)
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
        return img.gamma(exponent=1 / exp)

    def _numpy_impl(self, img):
        return np.power(img, self.exponents)


class ApplyLutImgOp(ImageOp):
    def __init__(self, lut):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.lut = lut

    def _vips_impl(self, img):

        lut = imglib_adapters.get((type(self.lut), VIPSImage))(self.lut[np.newaxis, :, :])
        return img.maplut(lut)


class RescaleImgOp(ImageOp):
    """Rescale a normalized float array to maximum admissible value for a given bit depth.

    Attributes
    ----------
    bitdepth: int
        Exponent used to rescale values so that out = in * (pow(2, bitdepth) - 1)
    """
    def __init__(self, bitdepth):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl
        self.bitdepth = bitdepth

    def dtype(self):
        if self.bitdepth > 16:
            return 'uint32'
        elif self.bitdepth > 8:
            return 'uint16'
        else:
            return 'uint8'

    def factor(self):
        return (2 ** self.bitdepth) - 1

    def _vips_impl(self, img):
        return img.linear([self.factor()], [0]).cast(dtype_to_vips_format[self.dtype()])

    def _numpy_impl(self, img):
        return (img * self.factor()).astype(np.dtype(self.dtype()))


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
        diff = (self.max_intensities - self.min_intensities)
        return 1. / np.where(diff == 0, 1e-30, diff)

    def _vips_impl(self, img):
        return img.linear(list(self.invdiff()), list(-self.min_intensities * self.invdiff()))

    def _numpy_impl(self, img):
        return (img - self.min_intensities) * self.invdiff()


class RescaleHistOp(ImageOp):
    """Rescale an histogram for a given bit depth.

    Attributes
    ----------
    bitdepth: int
        Exponent used to rescale values so that out = in * (pow(2, bitdepth) - 1)
    """
    def __init__(self, bitdepth):
        super().__init__()
        self._impl[np.ndarray] = self._numpy_impl
        self.bitdepth = bitdepth

    def _numpy_impl(self, hist):
        return hist.reshape((hist.shape[0], 2 ** self.bitdepth, -1)).sum(axis=2)


class ColorspaceImgOp(ImageOp):
    def __init__(self, colorspace):
        super().__init__()
        self._impl[VIPSImage] = self._vips_impl
        self.colorspace = colorspace

    def _vips_impl(self, img):
        new_colorspace = img.interpretation
        if self.colorspace == Colorspace.COLOR:
            new_colorspace = pyvips.enums.Interpretation.RGB
        elif self.colorspace == Colorspace.GRAY:
            new_colorspace = pyvips.enums.Interpretation.B_W

        if img.interpretation == pyvips.enums.Interpretation.RGB16 and self.colorspace == Colorspace.GRAY:
            new_colorspace = pyvips.enums.Interpretation.GREY16
        elif img.interpretation == pyvips.enums.Interpretation.GREY16 and self.colorspace == Colorspace.COLOR:
            new_colorspace = pyvips.enums.Interpretation.RGB16

        return img.colourspace(new_colorspace)


class ExtractChannelOp(ImageOp):
    def __init__(self, channel):
        super().__init__()
        self._impl[VIPSImage] = self._numpy_impl
        self.channel = channel

    def _numpy_impl(self, img):
        return img.extract_band(self.channel)


class ChannelReductionOp(ImageOp):
    def __init__(self, reduction):
        super().__init__()
        self._impl[VIPSImage] = self._numpy_impl
        self.reduction = reduction

    def __call__(self, obj, *args, **kwargs):
        if type(obj) is list and len(obj) > 0:
            type_obj = type(obj[0])
        else:
            type_obj = type(obj)

        if type_obj not in self.implementations:
            obj = self.implementation_adapters.get((type_obj, self.implementations[0]))(obj)

        return self._impl[type_obj](obj, *args, **kwargs)

    def _numpy_impl(self, imgs):
        if len(imgs) == 1:
            return imgs[0]
        format = imgs[0].format
        return VIPSImage.sum(imgs).cast(format)


class ColorspaceHistOp(ImageOp):
    def __init__(self, colorspace):
        super().__init__()
        self._impl[np.ndarray] = self._numpy_impl
        self.colorspace = colorspace

    def _numpy_impl(self, hist):
        hist = np.transpose(hist)

        if self.colorspace == Colorspace.GRAY and hist.shape[-1] != 1:
            return hist @ np.array([0.2125, 0.7154, 0.0721])
        elif self.colorspace == Colorspace.COLOR and hist.shape[-1] != 3:
            return np.dstack((hist, hist, hist))
        else:
            return hist


class TransparencyMaskImgOp(ImageOp):
    def __init__(self, bg_transparency, mask, bitdepth):
        super(TransparencyMaskImgOp, self).__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl

        self.bg_transparency = bg_transparency
        self.mask = mask
        self.bitdepth = bitdepth

    def factor(self):
        return (2 ** self.bitdepth) - 1

    def processed_mask(self, dtype):
        mask = self.mask.astype(dtype)
        mask[mask > 0] = 1 * self.factor()
        mask[mask == 0] = (1 - self.bg_transparency / 100) * self.factor()
        return mask

    def _vips_impl(self, img):
        mask = numpy_to_vips(self.processed_mask(vips_format_to_dtype[img.format]))
        return img.bandjoin(mask)

    def _numpy_impl(self, img):
        return np.dstack((img, self.processed_mask(img.dtype)))


class DrawOnImgOp(ImageOp):
    def __init__(self, draw, bitdepth, rgb_int_background=0):
        super(DrawOnImgOp, self).__init__()
        self._impl[VIPSImage] = self._vips_impl
        self._impl[np.ndarray] = self._numpy_impl

        self.draw = draw
        self.bitdepth = bitdepth
        self.rgb_int_background = rgb_int_background

    def _vips_impl(self, img):
        draw = numpy_to_vips(self.processed_draw(vips_format_to_dtype[img.format]))
        cond = numpy_to_vips(self.condition_mask())
        return cond.ifthenelse(img, draw)

    def _numpy_impl(self, img):
        draw = np.atleast_3d(self.processed_draw(img.dtype))
        cond = np.atleast_3d(self.condition_mask())
        return np.where(cond, img, draw)

    def processed_draw(self, dtype):
        draw = self.draw
        if self.bitdepth > 8:
            draw = draw.astype(np.float)
            draw /= 255
            draw *= self.factor()

        draw = draw.astype(dtype)
        return draw

    def condition_mask(self):
        """
        True -> image
        False -> drawing
        """
        if self.draw.ndim == 3:
            bg = np_int2rgb(self.rgb_int_background)
            return np.all(self.draw == np.asarray(bg), axis=-1).astype(np.uint8)
        else:
            mask = np.ones_like(self.draw, dtype=np.uint8)
            mask[self.draw != self.rgb_int_background] = 0
            return mask

    def factor(self):
        return (2 ** self.bitdepth) - 1


class RasterOp(ImageOp):
    @property
    def implementation_adapters(self):
        return dict()


class MaskRasterOp(RasterOp):
    def __init__(self, affine, out_width, out_height):
        super().__init__()
        self._impl[ParsedAnnotations] = self._default_impl

        self.affine_matrix = affine
        self.out_width = out_width
        self.out_height = out_height

    def _to_shape(self, annot, is_grayscale=True):
        geometry = affine_transform(annot.geometry, self.affine_matrix)
        value = annot.fill_color.as_rgb_tuple()[0] if is_grayscale else annot.fill_color.as_int()
        return geometry, value

    def _default_impl(self, annots):
        out_shape = (self.out_height, self.out_width)
        dtype = np.uint8 if annots.is_fill_grayscale else np.uint32

        def shape_generator():
            for annot in annots:
                yield self._to_shape(annot, annots.is_fill_grayscale)

        rasterized = rasterize(shape_generator(), out_shape=out_shape, dtype=dtype)
        if not annots.is_grayscale:
            return np_int2rgb(rasterized)
        return rasterized


class DrawRasterOp(RasterOp):
    def __init__(self, affine, out_width, out_height, point_style):
        super().__init__()
        self._impl[ParsedAnnotations] = self._default_impl

        self.affine_matrix = affine
        self.out_width = out_width
        self.out_height = out_height
        self.point_style = point_style

    @staticmethod
    def _contour_width(stroke_width, out_shape):
        return round(stroke_width * (0.75 + max(out_shape) / 1000))

    def _to_shape(self, annot, out_shape, is_grayscale=True):
        width = self._contour_width(annot.stroke_width, out_shape)
        geometry = stretch_contour(affine_transform(contour(annot.geometry, point_style=self.point_style),
                                                    self.affine_matrix), width=width)
        value = annot.stroke_color.as_rgb_tuple()[0] if is_grayscale else annot.stroke_color.as_int()
        return geometry, value

    def _default_impl(self, annots):
        out_shape = (self.out_height, self.out_width)
        dtype = np.uint8 if annots.is_stroke_grayscale else np.uint32

        def shape_generator():
            for annot in annots:
                if not annot.stroke_color:
                    continue
                yield self._to_shape(annot, out_shape, annots.is_stroke_grayscale)

        bg = self.background_color(annots)
        try:
            rasterized = rasterize(shape_generator(), out_shape=out_shape, dtype=dtype, fill=bg)
        except ValueError:
            # No valid geometry objects found for rasterize
            rasterized = np.full(out_shape, bg)
        if not annots.is_grayscale:
            return np_int2rgb(rasterized)
        return rasterized

    @staticmethod
    def background_color(annots):
        if annots.is_stroke_grayscale:
            values = [a.stroke_color.as_rgb_tuple()[0] for a in annots if a.stroke_color]
            return find_first_available_int(values, 0, 65536)
        else:
            values = [a.stroke_color.as_int() for a in annots if a.stroke_color]
            return find_first_available_int(values, 0, 4294967296)
