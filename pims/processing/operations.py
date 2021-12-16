#  * Copyright (c) 2020-2021. Authors: see NOTICE file.
#  *
#  * Licensed under the Apache License, Version 2.0 (the "License");
#  * you may not use this file except in compliance with the License.
#  * You may obtain a copy of the License at
#  *
#  *      http://www.apache.org/licenses/LICENSE-2.0
#  *
#  * Unless required by applicable law or agreed to in writing, software
#  * distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.
import logging
from abc import ABC
from typing import Any, Callable, Dict, List, Tuple, Union

import numpy as np
from pyvips import Image as VIPSImage, Size as VIPSSize  # noqa

from pims.api.utils.models import Colorspace
from pims.processing.adapters import RawImagePixels, RawImagePixelsType, imglib_adapters
from pims.utils.math import max_intensity

log = logging.getLogger("pims.processing")


class Op(ABC):
    """
    Base class for an operation.
    Operations are expected to be called like functions.
    """
    _impl: Dict[Any, Callable]

    def __init__(self):
        self._impl = {}

    @property
    def name(self):
        return self.__class__.__name__

    @property
    def parameters(self):
        return {
            k: v for (k, v) in self.__dict__.items()
            if not k.startswith("_")
        }

    @property
    def implementations(self) -> List[Any]:
        return list(self._impl.keys())

    def __call__(
        self, obj: Any, *args, **kwargs
    ) -> Any:
        return self._impl[type(obj)](obj, *args, **kwargs)


class ImageOp(Op):
    """
    Base class that all image operations derive from.

    Image operations are expected to be called like a function:
    `MyImgOp(param)(img)`.
    """
    _impl: Dict[RawImagePixelsType, Callable]

    @property
    def implementations(self) -> List[RawImagePixelsType]:
        return super(ImageOp, self).implementations

    @property
    def implementation_adapters(
        self
    ) -> Dict[Tuple[RawImagePixelsType, RawImagePixelsType], Callable]:
        return imglib_adapters

    def __call__(
        self, obj: RawImagePixels, *args, **kwargs
    ) -> Union[RawImagePixels, bytes]:
        """
        Apply image operation on given obj. Return type is a convertible
        image type (but not necessarily the type of `obj`).
        """
        # start = time.time()

        if type(obj) not in self.implementations:
            obj = self.implementation_adapters.get(
                (type(obj), self.implementations[0])
            )(obj)

        processed = self._impl[type(obj)](obj, *args, **kwargs)

        # end = time.time()
        # log.info(f"Apply {self.name} in {round((end - start) / 1e-6, 3)}µs")

        return processed


# class TransparencyMaskImgOp(ImageOp):
#     """
#     Add a transparency mask on image pixels
#     Modifies: number of channels (add alpha)
#     Out shape: width * height * (n_channels+1)
#     """
#     def __init__(self, bg_transparency: int, mask: np.ndarray, bitdepth: int):
#         super(TransparencyMaskImgOp, self).__init__()
#         self._impl[VIPSImage] = self._vips_impl
#         self._impl[np.ndarray] = self._numpy_impl
#
#         self.bg_transparency = bg_transparency
#         self.mask = mask
#         self.bitdepth = bitdepth
#
#     def processed_mask(self, dtype: np.dtype) -> np.ndarray:
#         mi = max_intensity(self.bitdepth)
#         mask = self.mask
#         if mask.ndim == 3:
#             mask = mask[:, :, 0]
#         mask = mask.astype(dtype)
#         mask[mask > 0] = 1 * mi
#         mask[mask == 0] = (1 - self.bg_transparency / 100) * mi
#         return mask
#
#     def _vips_impl(self, img: VIPSImage) -> VIPSImage:
#         mask = numpy_to_vips(
#             self.processed_mask(vips_format_to_dtype[img.format])
#         )
#         return img.bandjoin(mask)
#
#     def _numpy_impl(self, img: np.ndarray) -> np.ndarray:
#         return np.dstack((img, self.processed_mask(img.dtype)))
#
#
# class DrawOnImgOp(ImageOp):
#     """
#     Superpose a draw on image pixels.
#     Modifies: pixel intensities
#     Out shape: width * height * n_channels
#     """
#     def __init__(
#         self, draw: np.ndarray, bitdepth: int, rgb_int_background: int = 0
#     ):
#         super(DrawOnImgOp, self).__init__()
#         self._impl[VIPSImage] = self._vips_impl
#         self._impl[np.ndarray] = self._numpy_impl
#
#         self.draw = draw
#         self.bitdepth = bitdepth
#         self.rgb_int_background = rgb_int_background
#
#     def _vips_impl(self, img: VIPSImage) -> VIPSImage:
#         draw = numpy_to_vips(
#             self.processed_draw(vips_format_to_dtype[img.format])
#         )
#         cond = numpy_to_vips(self.condition_mask())
#         return cond.ifthenelse(img, draw)
#
#     def _numpy_impl(self, img: np.ndarray) -> np.ndarray:
#         draw = np.atleast_3d(self.processed_draw(img.dtype))
#         cond = np.atleast_3d(self.condition_mask())
#         return np.where(cond, img, draw)
#
#     def processed_draw(self, dtype: np.dtype) -> np.ndarray:
#         draw = self.draw
#         if self.bitdepth > 8:
#             draw = draw.astype(np.float)
#             draw /= 255
#             draw *= max_intensity(self.bitdepth)
#
#         draw = draw.astype(dtype)
#         return draw
#
#     def condition_mask(self) -> np.ndarray:
#         """
#         True -> image
#         False -> drawing
#         """
#         if self.draw.ndim == 3:
#             bg = np_int2rgb(self.rgb_int_background)
#             return np.all(self.draw == np.asarray(bg), axis=-1).astype(np.uint8)
#         else:
#             mask = np.ones_like(self.draw, dtype=np.uint8)
#             mask[self.draw != self.rgb_int_background] = 0
#             return mask


# class RasterOp(Op):
#     """
#     Base class for rasterization operations
#     """
#     _impl = Dict[ParsedAnnotations, Callable]
#
#     def __call__(
#         self, obj: ParsedAnnotations, *args, **kwargs
#     ) -> Union[RawImagePixels, bytes]:
#         return super().__call__(obj, *args, **kwargs)


class HistOp(Op):
    """
    Base class for histogram operations
    """
    _impl = Dict[np.ndarray, Callable]

    def __call__(
        self, obj: np.ndarray, *args, **kwargs
    ) -> np.ndarray:
        return super().__call__(obj, *args, **kwargs)


class RescaleHistOp(HistOp):
    """
    Rescale an histogram for a given bit depth. It is used to rescale values
    so that out = in * (pow(2, bitdepth) - 1)
    """

    def __init__(self, bitdepth: int):
        super().__init__()
        self._impl[np.ndarray] = self._numpy_impl
        self.bitdepth = bitdepth

    def _numpy_impl(self, hist: np.ndarray) -> np.ndarray:
        return hist.reshape(
            (hist.shape[0], max_intensity(self.bitdepth, count=True), -1)
        ).sum(axis=2)


class ColorspaceHistOp(HistOp):
    """
    Transform histogram colorspace if needed.
    """
    def __init__(self, colorspace: Colorspace):
        super().__init__()
        self._impl[np.ndarray] = self._numpy_impl
        self.colorspace = colorspace

    def _numpy_impl(self, hist: np.ndarray) -> np.ndarray:
        hist = np.transpose(hist)
        n_channels = hist.shape[-1]

        if self.colorspace == Colorspace.GRAY and n_channels != 1:
            n_used_channels = min(n_channels, 3)
            luminance = [0.2125, 0.7154, 0.0721]
            return hist[:n_used_channels] \
                @ np.array(luminance[:n_used_channels])
        elif self.colorspace == Colorspace.COLOR and n_channels != 3:
            return np.dstack((hist, hist, hist))
        else:
            return hist
