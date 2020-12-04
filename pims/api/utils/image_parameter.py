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
from connexion.exceptions import BadRequestProblem

from pims.api.utils.schema_format import parse_range, is_range


def get_rationed_resizing(resized, length, other_length):
    """
    Get resized lengths for `length` and `other_length` according to
    the ratio between `resized` and `length`.

    Parameters
    ----------
    resized : int or float
        Already resized length. If float, it is the ratio.
    length : int
        Non-resized length related to `resized`.
    other_length : int
        Other non-resized length to resize according the ratio.

    Returns
    -------
    resized : int
        First resized length according ratio.
    other_resized : int
        Other resized length according ratio.
    """
    ratio = resized if type(resized) == float else resized / length
    resized = resized if type(resized) == int else round(ratio * length)
    other_resized = round(ratio * other_length)
    return resized, other_resized


def get_output_dimensions(in_image, height=None, width=None, length=None):
    """
    Get output dimensions according, by order of precedence, either height,
    either width or the largest image length and such that ratio is preserved.

    Parameters
    ----------
    in_image : Image
        Input image with the aspect ratio to preserve.
    height : int or float (optional)
        Output height absolute size (int) or ratio (float)
    width : int or float (optional)
        Output width absolute size (int) or ratio (float).
        Ignored if `height` is not None.
    length : int or float (optional)
        Output largest side absolute size (int) or ratio (float).
        Ignored if `width` or `height` is not None.

    Returns
    -------
    out_width : int
        Output width preserving aspect ratio.
    out_height : int
        Output height preserving aspect ratio.

    Raises
    ------
    BadRequestProblem
        If it is impossible to determine output dimensions.
    """
    if height is not None:
        out_height, out_width = get_rationed_resizing(height, in_image.height, in_image.width)
    elif width is not None:
        out_width, out_height = get_rationed_resizing(width, in_image.width, in_image.height)
    elif length is not None:
        if in_image.width > in_image.height:
            out_width, out_height = get_rationed_resizing(length, in_image.width, in_image.height)
        else:
            out_height, out_width = get_rationed_resizing(length, in_image.height, in_image.width)
    else:
        raise BadRequestProblem(detail='Impossible to determine output dimensions. '
                                       'Height, width and length cannot all be unset.')

    return out_width, out_height


def parse_planes(planes_to_parse, n_planes, default=0, name='planes'):
    """
    Get a set of planes from a list of plane indexes and ranges.

    Parameters
    ----------
    planes_to_parse : list or None
        List of plane indexes and ranges to parse.
    n_planes : int
        Number of planes. It is the maximum output set size.
    default : int or list
        Plane index or list of plane indexes used as default set if `planes_to_parse` is empty (or None).
        Default is returned as a set but default values are expected to be in acceptable range.
    name : str
        Name of plane dimension (e.g. 'channels', 'z_slices', ...) used for exception messages.

    Returns
    -------
    set
        Set of valid plane indexes.

    Raises
    ------
    BadRequestProblem
        If an item of `planes_to_parse´ is invalid.
    """
    plane_indexes = list()

    if not planes_to_parse:
        return set(ensure_list(default))

    for plane in planes_to_parse:
        if type(plane) is int:
            plane_indexes.append(plane)
        elif is_range(plane):
            plane_indexes += [*parse_range(plane, 0, n_planes)]
        else:
            raise BadRequestProblem(detail='{} is not a valid index or range for {}.'.format(plane, name))
    return set([idx for idx in plane_indexes if 0 <= idx < n_planes])


def get_channel_indexes(image, planes):
    """
    Image channels used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, all channels are considered.
    """
    default = [*range(0, image.n_channels)]
    return parse_planes(planes, image.n_channels, default, 'channels')


def get_zslice_indexes(image, planes):
    """
    Image focal planes used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, the median focal plane is considered.
    """
    default = [round(image.depth / 2)]
    return parse_planes(planes, image.depth, default, 'z_slices')


def get_timepoint_indexes(image, planes):
    """
    Image timepoints used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, the first timepoint considered.
    """
    default = [0]
    return parse_planes(planes, image.duration, default, 'timepoints')


def check_reduction_validity(planes, reduction, name='planes'):
    """
    Verify if a reduction function is given when needed i.e. when
    the set of planes has a size > 1.

    Parameters
    ----------
    planes : set
        Set of planes
    reduction : str or None
        Reduction function to reduce the set of planes.
    name : str
        Name of plane dimension (e.g. 'channels', 'z_slices', ...) used for exception messages.

    Raises
    ------
    BadRequestProblem
        If no reduction function is given while needed.
    """
    if len(planes) > 1 and reduction is None:
        raise BadRequestProblem(detail='A reduction is required for {}'.format(name))


def check_array_size(iterable, allowed, nullable=True, name=None):
    """
    Verify an iterable has an allowed size or, optionally, is empty.

    Parameters
    ----------
    iterable : iterable
        Iterable which the size has to be verified.
    allowed : list of int
        Allowed iterable sizes
    nullable : boolean
        Whether no iterable at all is accepted or not.
    name : str (optional)
        Iterable name for exception messages.

    Raises
    ------
    BadRequestProblem
        If the iterable doesn't have one of the allowed sizes
        or is None if `nullable` is false.

    """
    if iterable is None:
        if not nullable:
            name = 'A parameter' if not name else name
            raise BadRequestProblem(detail="{} is unset while it is not allowed.".format(name))
        return

    if not len(iterable) in allowed:
        name = 'A parameter' if not name else name
        allowed_str = ', '.join([str(i) for i in allowed])
        raise BadRequestProblem("{} has a size of {} while only "
                                "these sizes are allowed: {}".format(name, len(iterable), allowed_str))


def ensure_list(value):
    """
    Ensure it is a list.

    Parameters
    ----------
    value : any
        Value to convert as a list

    Returns
    -------
    list
        The value converted as a list if it is not already the case.
    """
    if value is not None:
        return value if type(value) is list else [value]
    return value
