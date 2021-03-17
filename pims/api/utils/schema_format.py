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

import webcolors
from jsonschema import draft4_format_checker
from shapely.errors import WKTReadingError
from shapely.wkt import loads as wkt_loads


def is_int(value):
    try:
        int(value)
        return True
    except ValueError:
        return False


@draft4_format_checker.checks('range')
def is_range(value):
    """
    Whether a value is a PIMS range or not.
    Valid range examples: ":", "2:", ":2", "2:4"

    Parameters
    ----------
    value : str
        Value expected to be formatted as a range.

    Returns
    -------
    bool
        Whether it is a range.
    """
    if not isinstance(value, str):
        return False
    split = [v.strip() for v in value.split(':')]
    return len(split) == 2 and all([bound == '' or is_int(bound) for bound in split])


def parse_range(pims_range, mini, maxi):
    """
    Cast PIMS range to a Python range. Implicit low and high bounds
    are replace by `mini` and `maxi` respectively if necessary.

    Parameters
    ----------
    pims_range : str
        PIMS range to convert.
    mini : int
        Value replacing implicit low bound.
    maxi : int
        Value replacing implicit high bound.

    Returns
    -------
    range
        Python range, always in ascending order.

    Raises
    ------
    ValueError
        If `pims_range` is not a PIMS range.
    """
    if not is_range(pims_range):
        raise ValueError('Invalid literal for Range(): {}'.format(pims_range))

    low, high = [v.strip() for v in pims_range.split(':')]
    low = mini if low == '' else int(low)
    high = maxi if high == '' else int(high)

    low, high = min(low, high), max(low, high)
    return range(low, high)


@draft4_format_checker.checks('color')
def is_color(value):
    """
    Whether a value is a valid CSS3 color or not.
    Accepted values are:
    * hexadecimal (#FFF, #fff, #ffffff, ...)
    * int-rgb ( rgb(10,10,10), ...)
    * percent-rgb ( rgb(0%, 27.3%, 10%), ...)
    * CSS3 color names (red, blue, ...)

    Parameters
    ----------
    value : str
        Value expected to be a color

    Returns
    -------
    bool
        Whether it is a CSS3 color.
    """
    if not isinstance(value, str):
        return False
    try:
        parse_color(value)
        return True
    except ValueError:
        return False


def parse_color(value):
    """
    Parse a string to a valid CSS3 color.
    Accepted values are:
    * hexadecimal (#FFF, #fff, #ffffff, ...)
    * int-rgb ( rgb(10,10,10), ...)
    * percent-rgb ( rgb(0%, 27.3%, 10%), ...)
    * CSS3 color names (red, blue, ...)

    Parameters
    ----------
    value : str
        Value to be converted to a color

    Returns
    -------
    color : IntegerRGB
        The RGB color

    Raises
    ------
    ValueError
        If `value` cannot be parsed to a CSS3 color.
    """

    try:
        return webcolors.name_to_rgb(value)
    except ValueError:
        pass

    try:
        return webcolors.hex_to_rgb(value)
    except ValueError:
        pass

    if value[:4].lower() == 'rgb(' and value[-1] == ')':
        try:
            triplet = (int(c) for c in value[4:-1].split(','))
            return webcolors.normalize_integer_triplet(triplet)
        except ValueError:
            # cannot parse values in the triplet
            pass

        try:
            triplet = (c for c in value[4:-1].split(','))
            percent_rgb = webcolors.normalize_percent_triplet(triplet)
            return webcolors.rgb_percent_to_rgb(percent_rgb)
        except ValueError:
            pass

    raise ValueError("Invalid literal for Color: {}".format(value))


@draft4_format_checker.checks('wkt')
def is_wkt(value):
    """
    Whether a value is a Well-Known Text string.
    The underlying geometry validity is not checked.

    Parameters
    ----------
    value : str
        Value expected to be a WKT string.

    Returns
    -------
    bool
        Whether the value is a WKT string or not
    """
    try:
        wkt_loads(str(value))
        return True
    except WKTReadingError:
        return False
