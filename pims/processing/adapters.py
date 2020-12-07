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

from pyvips import Image as VIPSImage
from PIL import Image as PILImage

import numpy as np

from pims.formats.utils.vips import dtype_to_vips_format, vips_format_to_dtype


def numpy_to_vips(np_array, *args, width=None, height=None, n_channels=None, **kwargs):
    """
    Convert a Numpy array to a VIPS image.

    Parameters
    ----------
    np_array : array-like
        Numpy array to convert. If 1D, it is expected it contains flattened image data.
    args
    width : int (optional)
        If `np_array` is 1D, width of the image.
    height : int (optional)
        If `np_array` is 1D, height of the image.
    n_channels : int (optional)
        If `np_array` is 1D, number of channels in the image.
    kwargs

    Returns
    -------
    VIPSImage
        VIPS image representation of the array

    Raises
    ------
    ValueError
        If it is impossible to convert provided array.
    """
    vips_format = dtype_to_vips_format[str(np_array.dtype)]
    if np_array.ndim == 1:
        if width * height * n_channels == np_array.size:
            return VIPSImage.new_from_memory(np_array.data, width, height, n_channels, vips_format)
        raise ValueError("Cannot convert {} to VIPS image".format(np_array))
    elif np_array.ndim == 2:
        height, width = np_array.shape
        n_channels = 1
    elif np_array.ndim == 3:
        height, width, n_channels = np_array.shape
    else:
        raise NotImplementedError

    flat = np_array.reshape(np_array.size)
    return VIPSImage.new_from_memory(flat.data, width, height, n_channels, vips_format)


def numpy_to_pil(np_array, *args, **kwargs):
    pass


def pil_to_vips(pil_image, *args, **kwargs):
    pass


def pil_to_numpy(pil_image, *args, **kwargs):
    pass


def vips_to_numpy(vips_image, *args, **kwargs):
    """
    Convert a VIPS image to a Numpy array.
    Parameters
    ----------
    vips_image : VIPSImage
        VIPS image to convert
    args
    kwargs

    Returns
    -------
    arr : Numpy array
        Array representation of VIPS image. Shape is always (height, width, bands).
    """
    return np.ndarray(buffer=vips_image.write_to_memory(),
                      dtype=vips_format_to_dtype[vips_image.format],
                      shape=[vips_image.height, vips_image.width, vips_image.bands])


def vips_to_pil(vips_image, *args, **kwargs):
    pass


def identity(v, *args, **kwargs):
    return v


imglib_adapters = {
    (np.ndarray, VIPSImage): numpy_to_vips,
    (np.ndarray, PILImage): numpy_to_pil,
    (np.ndarray, np.ndarray): identity,
    (PILImage, VIPSImage): pil_to_vips,
    (PILImage, np.ndarray): pil_to_numpy,
    (PILImage, PILImage): identity,
    (VIPSImage, np.ndarray): vips_to_numpy,
    (VIPSImage, PILImage): vips_to_pil,
    (VIPSImage, VIPSImage): identity
}
