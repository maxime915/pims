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

import numpy as np


def rgb2int(rgb):
    """
    Convert a triplet 8-bit RGB to a 32-bit integer.

    Parameters
    ----------
    rgb : IntegerRGB
        RGB triplet with values in range 0-255.

    Returns
    -------
    color_int : int
        Color representation as a 32-bit integer.
    """
    r, g, b = rgb
    return (r & 255) << 16 | (g & 255) << 8 | (b & 255) << 0


def int2rgb(color_int):
    """
    Convert a 32-bit int color to a 8-bit RGB triplet.

    Parameters
    ----------
    color_int : int, array-like
        Integer value(s) to convert

    Returns
    -------
    rgb : array-like
        Color representation as a RGB triplet.
        Output shape is `color_int.shape + (3,)`.
    """
    r = color_int >> 16 & 255
    g = color_int >> 8 & 255
    b = color_int >> 0 & 255
    return np.squeeze(np.dstack((r, g, b)))
