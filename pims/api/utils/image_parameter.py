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

from ordered_set import OrderedSet

from pims.api.exceptions import TooLargeOutputProblem
from pims.api.utils.schema_format import parse_range, is_range
from pims.processing.region import Region


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


def get_thumb_output_dimensions(in_image, height=None, width=None, length=None, zoom=None, level=None):
    """
    Get output dimensions according, by order of precedence, either height,
    either width, either the largest image length, either zoom or level and such that ratio is preserved.

    Parameters
    ----------
    in_image : Image
        Input image with the aspect ratio to preserve.
    height : int or float (optional)
        Output height absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` is not None.
    width : int or float (optional)
        Output width absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `height` is not None.
    length : int or float (optional)
        Output largest side absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `width` or `height` is not None.
    zoom : int (optional)
        Output zoom tier to consider as size.
        The zoom tier is expected to be valid for the input image.
        Ignored if `level` is not None.
    level : int (optional)
        Output level tier to consider as size.
        The level tier is expected to be valid for the input image.

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
    if level is not None:
        tier = in_image.pyramid.get_tier_at_level(level)
        out_height, out_width = tier.height, tier.width
    elif zoom is not None:
        tier = in_image.pyramid.get_tier_at_zoom(zoom)
        out_height, out_width = tier.height, tier.width
    elif height is not None:
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


def get_window_output_dimensions(in_image, region, height=None, width=None, length=None, zoom=None, level=None):
    """
    Get output dimensions according, by order of precedence, either height,
    either width, either the largest image length, either zoom or level and such that region ratio is preserved.

    Parameters
    ----------
    in_image : Image
        Input image from which region is extracted.
    region : Region
        Input region with aspect ratio to preserve.
    height : int or float (optional)
        Output height absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` is not None.
    width : int or float (optional)
        Output width absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `height` is not None.
    length : int or float (optional)
        Output largest side absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `width` or `height` is not None.
    zoom : int (optional)
        Output zoom tier to consider as size.
        The zoom tier is expected to be valid for the input image.
        Ignored if `level` is not None.
    level : int (optional)
        Output level tier to consider as size.
        The level tier is expected to be valid for the input image.

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
    if level is not None:
        tier = in_image.pyramid.get_tier_at_level(level)
        out_height, out_width = round(region.height / tier.height_factor), round(region.width / tier.width_factor)
    elif zoom is not None:
        tier = in_image.pyramid.get_tier_at_zoom(zoom)
        out_height, out_width = round(region.height / tier.height_factor), round(region.width / tier.width_factor)
    elif height is not None:
        out_height, out_width = get_rationed_resizing(height, region.height, region.width)
    elif width is not None:
        out_width, out_height = get_rationed_resizing(width, region.width, region.height)
    elif length is not None:
        if region.width > region.height:
            out_width, out_height = get_rationed_resizing(length, region.width, region.height)
        else:
            out_height, out_width = get_rationed_resizing(length, region.height, region.width)
    else:
        raise BadRequestProblem(detail='Impossible to determine output dimensions. '
                                       'Height, width and length cannot all be unset.')

    return out_width, out_height


def safeguard_output_dimensions(safe_mode, max_size, width, height):
    """
    Safeguard image output dimensions according to safe mode and maximum
    admissible size.

    Parameters
    ----------
    safe_mode : str (SAFE_REJECT, SAFE_RESIZE, UNSAFE)
        How to handle too large image response. See API specification for details.
    max_size : int
        Maximum admissible size when mode is SAFE_*
    width : int
        Expected output width
    height : int
        Expected output height

    Returns
    -------
    width : int
        Safeguarded output width according to mode.
    height : int
        Safeguarded output height according to mode.

    Raises
    ------
    TooLargeOutputProblem
        If mode is SAFE_REJECT and the expect output size is unsafe.
    """
    if safe_mode == 'UNSAFE':
        return width, height
    elif safe_mode == 'SAFE_REJECT' and (width > max_size or height > max_size):
        raise TooLargeOutputProblem(width, height, max_size)
    elif safe_mode == 'SAFE_RESIZE' and (width > max_size or height > max_size):
        if width > height:
            return get_rationed_resizing(max_size, width, height)
        else:
            height, width = get_rationed_resizing(max_size, height, width)
            return width, height
    else:
        return width, height


def parse_region(in_image, region, tier_idx, tier_type):
    """
    Parse a region and return normalized region in [0,1]

    Parameters
    ----------
    in_image : Image
        Image in which region is extracted
    region : Region
        Region to parse
    tier_idx : int
        Tier index to use as reference
    tier_type: string (`LEVEL` or `ZOOM`)
        Type of tier index

    Returns
    -------
    norm_region: Region
        The normalized region

    Raises
    ------
    BadRequestProblem
        If a region coordinate is out of bound.
    """
    if tier_type == "ZOOM":
        check_zoom_validity(in_image.pyramid, tier_idx)
        ref_tier = in_image.pyramid.get_tier_at_zoom(tier_idx)
    else:
        check_level_validity(in_image.pyramid, tier_idx)
        ref_tier = in_image.pyramid.get_tier_at_level(tier_idx)

    normalized = dict()
    region_dict = region.asdict()
    for item in ("left", "width"):
        if type(region_dict[item]) == int:
            normalized[item] = region_dict[item] / ref_tier.width
        else:
            normalized[item] = region_dict[item] / ref_tier.width_factor

    for item in ("top", "height"):
        if type(region_dict[item]) == int:
            normalized[item] = region_dict[item] / ref_tier.height
        else:
            normalized[item] = region_dict[item] / ref_tier.height_factor

    normalized = Region(**normalized)
    for coord in (normalized.top, normalized.bottom, normalized.left, normalized.right):
        if not 0 <= coord <= 1:
            raise BadRequestProblem(detail="Some coordinates of region {} are out of bounds.".format(region))

    return normalized


def parse_planes(planes_to_parse, n_planes, default=0, name='planes'):
    """
    Get a set of planes from a list of plane indexes and ranges.

    Parameters
    ----------
    planes_to_parse : list
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

    if len(planes_to_parse) == 0:
        return OrderedSet(ensure_list(default))

    for plane in planes_to_parse:
        if type(plane) is int:
            plane_indexes.append(plane)
        elif is_range(plane):
            plane_indexes += [*parse_range(plane, 0, n_planes)]
        else:
            raise BadRequestProblem(detail='{} is not a valid index or range for {}.'.format(plane, name))
    return OrderedSet([idx for idx in plane_indexes if 0 <= idx < n_planes])


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
    return []


def parse_intensity_bounds(image, out_channels, min_intensities, max_intensities, allow_none=False):
    """
    Parse intensity parameters according to a specific image.

    Parameters
    ----------
    image : Image
        Input image used to determine minimum and maximum admissible values per channel.
    out_channels: list of int
        Channel indexes expected in the output, used for intensities.
    min_intensities : list of int (optional) or str (optional)
        List of minimum intensities. See API spec for admissible string constants.
    max_intensities : list of int (optional) or str (optional)
        List of maximum intensities. See API spec for admissible string constants.
    allow_none : bool
        Whether the NONE string constant is admissible or not.

    Returns
    -------
    parsed_min_intensities : list of int
        Parsed min intensities. List size is the number of channels in the image output.
    parsed_max_intensities : list of int
        Parsed max intensities. List size is the number of channels in the image output.
    """
    bit_depth = image.significant_bits
    max_allowed_intensity = 2 ** bit_depth - 1
    n_out_channels = len(out_channels)

    if len(min_intensities) == 0:
        min_intensities = [0] * n_out_channels
    elif len(min_intensities) == 1:
        min_intensities = min_intensities * n_out_channels

    if len(max_intensities) == 0:
        max_intensities = [max_allowed_intensity] * n_out_channels
    elif len(max_intensities) == 1:
        max_intensities = max_intensities * n_out_channels
    
    def parse_intensity(c, bound_value, bound_default, bound_kind):
        if type(bound_value) is int:
            if bound_value < 0:
                return 0
            elif bound_value > max_allowed_intensity:
                return max_allowed_intensity
            else:
                return intensity
        else:
            if allow_none and bound_value == "NONE":
                return bound_default
            elif bound_value == "AUTO_IMAGE":
                if image.significant_bits <= 8:
                    return bound_default
                else:
                    return image.channel_stats(c)[bound_kind]
            elif bound_value == "STRETCH_IMAGE":
                return image.channel_stats(c)[bound_kind]
            else:
                # TODO: AUTO_PLANE, STRETCH_PLANE
                return bound_default

    for idx, (channel, intensity) in enumerate(zip(out_channels, min_intensities)):
        min_intensities[idx] = parse_intensity(channel, intensity, 0, "minimum")

    for idx, (channel, intensity) in enumerate(zip(out_channels, max_intensities)):
        max_intensities[idx] = parse_intensity(channel, intensity, max_allowed_intensity, "maximum")

    return min_intensities, max_intensities


def check_level_validity(pyramid, level):
    """ Check the level tier exists in the image pyramid.

    Parameters
    ----------
    pyramid : Pyramid
        Image pyramid
    level : int or None
        Level to be checked for existence in the image pyramid

    Raises
    ------
    BadRequestProblem
        If the given level is not in the image pyramid.
    """

    if level is not None and not 0 <= level <= pyramid.max_level:
        raise BadRequestProblem(detail="Level tier {} does not exist.".format(level))


def check_zoom_validity(pyramid, zoom):
    """Check the zoom tier exists in the image pyramid.

    Parameters
    ----------
    pyramid : Pyramid
        Image pyramid
    zoom : int or None
        Zoom to be checked for existence in the image pyramid

    Raises
    ------
    BadRequestProblem
        If the given zoom is not in the image pyramid.
    """

    if zoom is not None and not 0 <= zoom <= pyramid.max_zoom:
        raise BadRequestProblem(detail="Zoom tier {} does not exist.".format(zoom))


def check_tileindex_validity(pyramid, ti, tier_idx, tier_type):
    """
    Check the tile index exists in the image pyramid at given tier.

    Parameters
    ----------
    pyramid : Pyramid
        Image pyramid
    ti : int
        Tile index to check
    tier_idx : int
        Tier index in the pyramid expected to contain the tile
    tier_type : str (`LEVEL` or `ZOOM`)
        Tier type

    Raises
    ------
    BadRequestProblem
        If the tile index is invalid.
    """
    if tier_type == "ZOOM":
        check_zoom_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_zoom(tier_idx)
    else:
        check_level_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_level(tier_idx)

    if not 0 <= ti < ref_tier.max_ti:
        raise BadRequestProblem("Tile index {} is invalid for tier {}.".format(ti, ref_tier))


def check_tilecoord_validity(pyramid, tx, ty, tier_idx, tier_type):
    """
    Check the tile index exists in the image pyramid at given tier.

    Parameters
    ----------
    pyramid : Pyramid
        Image pyramid
    tx : int
        Tile coordinate along X axis to check
    ty : int
        Tile coordinate along Y axis to check
    tier_idx : int
        Tier index in the pyramid expected to contain the tile
    tier_type : str (`LEVEL` or `ZOOM`)
        Tier type

    Raises
    ------
    BadRequestProblem
        If the tile index is invalid.
    """
    if tier_type == "ZOOM":
        check_zoom_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_zoom(tier_idx)
    else:
        check_level_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_level(tier_idx)

    if not 0 <= tx < ref_tier.max_tx:
        raise BadRequestProblem("Tile coordinate {} along X axis is invalid for tier {}.".format(tx, ref_tier))

    if not 0 <= ty < ref_tier.max_ty:
        raise BadRequestProblem("Tile coordinate {} along Y axis is invalid for tier {}.".format(ty, ref_tier))


def parse_bitdepth(in_image, bits):
    return in_image.significant_bits if bits == "AUTO" else bits
