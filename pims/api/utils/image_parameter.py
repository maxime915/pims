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
from __future__ import annotations

from copy import copy
from typing import Iterable, List, Optional, Sized, TYPE_CHECKING, Tuple, Type, Union

from pims.api.exceptions import (
    BadRequestException, ColormapNotFoundProblem,
    FilterNotFoundProblem, TooLargeOutputProblem
)
from pims.api.utils.header import SafeMode
from pims.api.utils.models import (
    BitDepthEnum, ChannelReduction, ColormapEnum, ColormapId, GenericReduction,
    IntensitySelectionEnum, TierIndexType
)
from pims.api.utils.range_parameter import is_range, parse_range
from pims.files.image import Image
from pims.formats.utils.structures.metadata import ImageChannel
from pims.formats.utils.structures.pyramid import Pyramid
from pims.processing.colormaps import ColorColormap, Colormap, ColormapsByName
from pims.processing.region import Region
from pims.utils.color import Color
from pims.utils.iterables import ensure_list
from pims.utils.math import get_rationed_resizing

if TYPE_CHECKING:
    from pims.filters import AbstractFilter, FiltersById


Size = Union[int, float]


def get_thumb_output_dimensions(
    in_image: Image, height: Optional[Size] = None, width: Optional[Size] = None,
    length: Optional[Size] = None, zoom: Optional[int] = None, level: Optional[int] = None,
    allow_upscaling: bool = True
) -> Tuple[int, int]:
    """
    Get output dimensions according, by order of precedence, either height, either width,
    either the largest image length, either zoom or level and such that ratio is preserved.

    Parameters
    ----------
    in_image
        Input image with the aspect ratio to preserve.
    height
        Output height absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` is not None.
    width
        Output width absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `height` is not None.
    length
        Output largest side absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `width` or `height` is not None.
    zoom
        Output zoom tier to consider as size.
        The zoom tier is expected to be valid for the input image.
        Ignored if `level` is not None.
    level
        Output level tier to consider as size.
        The level tier is expected to be valid for the input image.
    allow_upscaling
        Whether the output thumb size can be greater than the input image size.
        If upscaling is not allowed, maximum thumb size is the input image size.

    Returns
    -------
    out_width
        Output width preserving aspect ratio.
    out_height
        Output height preserving aspect ratio.

    Raises
    ------
    BadRequestException
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
        raise BadRequestException(
            detail='Impossible to determine output dimensions. '
                   'Height, width and length cannot all be unset.'
        )

    if not allow_upscaling and (out_width > in_image.width or out_height > in_image.height):
        return in_image.width, in_image.height

    return out_width, out_height


def get_window_output_dimensions(
    in_image: Image, region: Region, height: Optional[Size] = None, width: Optional[Size] = None,
    length: Optional[Size] = None, zoom: Optional[int] = None, level: Optional[int] = None
) -> Tuple[int, int]:
    """
    Get output dimensions according, by order of precedence, either height, either width,
    either the largest image length, either zoom or level and such that region ratio is preserved.

    Parameters
    ----------
    in_image
        Input image from which region is extracted.
    region
        Input region with aspect ratio to preserve.
    height
        Output height absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` is not None.
    width
        Output width absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `height` is not None.
    length
        Output largest side absolute size (int) or ratio (float).
        Ignored if `level` or `zoom` or `width` or `height` is not None.
    zoom
        Output zoom tier to consider as size.
        The zoom tier is expected to be valid for the input image.
        Ignored if `level` is not None.
    level
        Output level tier to consider as size.
        The level tier is expected to be valid for the input image.

    Returns
    -------
    out_width
        Output width preserving aspect ratio.
    out_height
        Output height preserving aspect ratio.

    Raises
    ------
    BadRequestException
        If it is impossible to determine output dimensions.
    """
    if level is not None:
        tier = in_image.pyramid.get_tier_at_level(level)
        out_height, out_width = round(region.true_height / tier.height_factor), round(
            region.true_width / tier.width_factor
            )
    elif zoom is not None:
        tier = in_image.pyramid.get_tier_at_zoom(zoom)
        out_height, out_width = round(region.true_height / tier.height_factor), round(
            region.true_width / tier.width_factor
            )
    elif height is not None:
        out_height, out_width = get_rationed_resizing(
            height, int(region.true_height), int(region.true_width)
        )
    elif width is not None:
        out_width, out_height = get_rationed_resizing(
            width, int(region.true_width), int(region.true_height)
        )
    elif length is not None:
        if region.true_width > region.true_height:
            out_width, out_height = get_rationed_resizing(
                length, int(region.true_width), int(region.true_height)
            )
        else:
            out_height, out_width = get_rationed_resizing(
                length, int(region.true_height), int(region.true_width)
            )
    else:
        raise BadRequestException(
            detail='Impossible to determine output dimensions. '
                   'Height, width and length cannot all be unset.'
        )

    return out_width, out_height


def safeguard_output_dimensions(
    safe_mode: SafeMode, max_size: int, width: int, height: int
) -> Tuple[int, int]:
    """
    Safeguard image output dimensions according to safe mode and maximum
    admissible size.

    Parameters
    ----------
    safe_mode : SafeMode
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
    if safe_mode == SafeMode.UNSAFE:
        return width, height
    elif safe_mode == SafeMode.SAFE_REJECT and (width > max_size or height > max_size):
        raise TooLargeOutputProblem(width, height, max_size)
    elif safe_mode == SafeMode.SAFE_RESIZE and (width > max_size or height > max_size):
        if width > height:
            return get_rationed_resizing(max_size, width, height)
        else:
            height, width = get_rationed_resizing(max_size, height, width)
            return width, height
    else:
        return width, height


def parse_region(
    in_image: Image, top: Size, left: Size, width: Size, height: Size, tier_idx: int = 0,
    tier_type: TierIndexType = TierIndexType.LEVEL, silent_oob: bool = False
) -> Region:
    """
    Parse a region

    Parameters
    ----------
    in_image
        Image in which region is extracted
    top
    left
    width
    height
    tier_idx
        Tier index to use as reference
    tier_type
        Type of tier index
    silent_oob
        Whether out of bounds region should raise an error or not.

    Returns
    -------
    region
        The parsed region

    Raises
    ------
    BadRequestException
        If a region coordinate is out of bound and silent_oob is False.
    """
    if tier_type == TierIndexType.ZOOM:
        check_zoom_validity(in_image.pyramid, tier_idx)
        ref_tier = in_image.pyramid.get_tier_at_zoom(tier_idx)
    else:
        check_level_validity(in_image.pyramid, tier_idx)
        ref_tier = in_image.pyramid.get_tier_at_level(tier_idx)

    if type(top) == float:
        top *= ref_tier.height
    if type(left) == float:
        left *= ref_tier.width
    if type(width) == float:
        width *= ref_tier.width
    if type(height) == float:
        height *= ref_tier.height

    downsample = (ref_tier.width_factor, ref_tier.height_factor)
    region = Region(top, left, width, height, downsample)

    if not silent_oob:
        clipped = copy(region).clip(ref_tier.width, ref_tier.height)
        if clipped != region:
            raise BadRequestException(
                detail=f"Some coordinates of region {region} are out of bounds."
            )

    return region


def parse_planes(
    planes_to_parse: List[int], n_planes: int, default: Union[int, List[int]] = 0,
    name: str = 'planes'
) -> List[int]:
    """
    Get a set of planes from a list of plane indexes and ranges.

    Parameters
    ----------
    planes_to_parse
        List of plane indexes and ranges to parse.
    n_planes
        Number of planes. It is the maximum output set size.
    default
        Plane index or list of plane indexes used as default set if `planes_to_parse` is empty.
        Default is returned as a set but default values are expected to be in acceptable range.
    name
        Name of plane dimension (e.g. 'channels', 'z_slices', ...) used for exception messages.

    Returns
    -------
    plane_set
        Ordered list of valid plane indexes (where duplicates have been removed).

    Raises
    ------
    BadRequestException
        If an item of `planes_to_parse´ is invalid.
        If the set of valid planes is empty
    """
    plane_indexes = list()

    if len(planes_to_parse) == 0:
        return sorted(set((ensure_list(default))))

    for plane in planes_to_parse:
        if type(plane) is int:
            plane_indexes.append(plane)
        elif is_range(plane):
            plane_indexes += [*parse_range(plane, 0, n_planes)]
        else:
            raise BadRequestException(
                detail=f'{plane} is not a valid index or range for {name}.'
            )
    plane_set = sorted(set([idx for idx in plane_indexes if 0 <= idx < n_planes]))
    if len(plane_set) == 0:
        raise BadRequestException(detail=f"No valid indexes for {name}")
    return plane_set


def get_channel_indexes(image: Image, planes: List[int]) -> List[int]:
    """
    Image channels used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, all channels are considered.
    """
    default = [*range(0, image.n_channels)]
    return parse_planes(planes, image.n_channels, default, 'channels')


def get_zslice_indexes(image: Image, planes: List[int]) -> List[int]:
    """
    Image focal planes used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, the median focal plane is considered.
    """
    default = [round(image.depth / 2)]
    return parse_planes(planes, image.depth, default, 'z_slices')


def get_timepoint_indexes(image: Image, planes: List[int]) -> List[int]:
    """
    Image timepoints used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, the first timepoint considered.
    """
    default = [0]
    return parse_planes(planes, image.duration, default, 'timepoints')


def check_reduction_validity(
    planes: List[int], reduction: Optional[Union[GenericReduction, ChannelReduction]],
    name: str = 'planes'
):
    """
    Verify if a reduction function is given when needed i.e. when
    the set of planes has a size > 1.

    Parameters
    ----------
    planes
        Set of planes
    reduction
        Reduction function to reduce the set of planes.
    name
        Name of plane dimension (e.g. 'channels', 'z_slices', ...) used for exception messages.

    Raises
    ------
    BadRequestException
        If no reduction function is given while needed.
    """
    if len(planes) > 1 and reduction is None:
        raise BadRequestException(detail=f'A reduction is required for {name}')


def check_array_size(
    iterable: Optional[Sized], allowed: List[int], nullable: bool = True,
    name: Optional[str] = None
):
    """
    Verify an iterable has an allowed size or, optionally, is empty.

    Parameters
    ----------
    iterable
        Iterable which the size has to be verified.
    allowed
        Allowed iterable sizes
    nullable
        Whether no iterable at all is accepted or not.
    name
        Iterable name for exception messages.

    Raises
    ------
    BadRequestException
        If the iterable doesn't have one of the allowed sizes
        or is None if `nullable` is false.

    """
    if iterable is None:
        if not nullable:
            name = 'A parameter' if not name else name
            raise BadRequestException(detail=f"{name} is unset while it is not allowed.")
        return

    if not len(iterable) in allowed:
        name = 'A parameter' if not name else name
        allowed_str = ', '.join([str(i) for i in allowed])
        raise BadRequestException(
            f'{name} has a size of {len(iterable)} '
            f'while only these sizes are allowed: {allowed_str}'
        )


Intensities = List[Union[int, str]]


def parse_intensity_bounds(
    image: Image, out_channels: List[int], out_zslices: List[int], out_timepoints: List[int],
    min_intensities: Intensities, max_intensities: Intensities, allow_none: bool = False
) -> Tuple[List[int], List[int]]:
    """
    Parse intensity parameters according to a specific image.

    Parameters
    ----------
    image
        Input image used to determine minimum and maximum admissible values per channel.
    out_channels
        Channel indexes expected in the output, used for intensities.
    out_zslices
        Z slices indexes expected in the output, used for AUTO_PLANE and STRETCH_PLANE.
    out_timepoints
        Timepoint indexes expected in the output, used for AUTO_PLANE ans STRETCH_PLANE.
    min_intensities
        List of minimum intensities. See API spec for admissible string constants.
    max_intensities
        List of maximum intensities. See API spec for admissible string constants.
    allow_none
        Whether the NONE string constant is admissible or not.

    Returns
    -------
    parsed_min_intensities
        Parsed min intensities. List size is the number of channels in the image output.
    parsed_max_intensities
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
        bound_kind_idx = 0 if bound_kind == "minimum" else 1

        def stretch_plane():
            bounds = []
            for z in out_zslices:
                for t in out_timepoints:
                    bounds.append(image.plane_bounds(c, z, t)[bound_kind_idx])
            func = min if bound_kind == "minimum" else max
            return func(bounds)

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
            elif bound_value == IntensitySelectionEnum.AUTO_IMAGE:
                if image.significant_bits <= 8:
                    return bound_default
                else:
                    return image.channel_bounds(c)[bound_kind_idx]
            elif bound_value == IntensitySelectionEnum.STRETCH_IMAGE:
                return image.channel_bounds(c)[bound_kind_idx]
            elif bound_value == IntensitySelectionEnum.AUTO_PLANE:
                if image.significant_bits <= 8:
                    return bound_default
                else:
                    return stretch_plane()
            elif bound_value == IntensitySelectionEnum.STRETCH_PLANE:
                return stretch_plane()
            else:
                return bound_default

    for idx, (channel, intensity) in enumerate(zip(out_channels, min_intensities)):
        min_intensities[idx] = parse_intensity(channel, intensity, 0, "minimum")

    for idx, (channel, intensity) in enumerate(zip(out_channels, max_intensities)):
        max_intensities[idx] = parse_intensity(
            channel, intensity, max_allowed_intensity, "maximum"
        )

    return min_intensities, max_intensities


def check_level_validity(pyramid: Pyramid, level: Optional[int]):
    """ Check the level tier exists in the image pyramid.

    Parameters
    ----------
    pyramid : Pyramid
        Image pyramid
    level : int or None
        Level to be checked for existence in the image pyramid

    Raises
    ------
    BadRequestException
        If the given level is not in the image pyramid.
    """

    if level is not None and not 0 <= level <= pyramid.max_level:
        raise BadRequestException(detail=f"Level tier {level} does not exist.")


def check_zoom_validity(pyramid: Pyramid, zoom: Optional[int]):
    """Check the zoom tier exists in the image pyramid.

    Parameters
    ----------
    pyramid : Pyramid
        Image pyramid
    zoom : int or None
        Zoom to be checked for existence in the image pyramid

    Raises
    ------
    BadRequestException
        If the given zoom is not in the image pyramid.
    """

    if zoom is not None and not 0 <= zoom <= pyramid.max_zoom:
        raise BadRequestException(detail=f"Zoom tier {zoom} does not exist.")


def check_tileindex_validity(pyramid: Pyramid, ti: int, tier_idx: int, tier_type: TierIndexType):
    """
    Check the tile index exists in the image pyramid at given tier.

    Parameters
    ----------
    pyramid
        Image pyramid
    ti
        Tile index to check
    tier_idx
        Tier index in the pyramid expected to contain the tile
    tier_type
        Tier type

    Raises
    ------
    BadRequestException
        If the tile index is invalid.
    """
    if tier_type == TierIndexType.ZOOM:
        check_zoom_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_zoom(tier_idx)
    else:
        check_level_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_level(tier_idx)

    if not 0 <= ti < ref_tier.max_ti:
        raise BadRequestException(f"Tile index {ti} is invalid for tier {ref_tier}.")


def check_tilecoord_validity(
    pyramid: Pyramid, tx: int, ty: int, tier_idx: int, tier_type: TierIndexType
):
    """
    Check the tile index exists in the image pyramid at given tier.

    Parameters
    ----------
    pyramid
        Image pyramid
    tx
        Tile coordinate along X axis to check
    ty
        Tile coordinate along Y axis to check
    tier_idx
        Tier index in the pyramid expected to contain the tile
    tier_type
        Tier type

    Raises
    ------
    BadRequestException
        If the tile index is invalid.
    """
    if tier_type == TierIndexType.ZOOM:
        check_zoom_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_zoom(tier_idx)
    else:
        check_level_validity(pyramid, tier_idx)
        ref_tier = pyramid.get_tier_at_level(tier_idx)

    if not 0 <= tx < ref_tier.max_tx:
        raise BadRequestException(
            f"Tile coordinate {tx} along X axis is invalid for tier {ref_tier}."
        )

    if not 0 <= ty < ref_tier.max_ty:
        raise BadRequestException(
            f"Tile coordinate {ty} along Y axis is invalid for tier {ref_tier}."
        )


def parse_bitdepth(in_image: Image, bits: Union[int, BitDepthEnum]) -> int:
    return in_image.significant_bits if bits == BitDepthEnum.AUTO else bits


def parse_filter_ids(
    filter_ids: Iterable[str], existing_filters: FiltersById
) -> List[Type[AbstractFilter]]:
    filters = []
    for filter_id in filter_ids:
        try:
            filters.append(existing_filters[filter_id.upper()])
        except KeyError:
            raise FilterNotFoundProblem(filter_id)
    return filters


def parse_colormap_ids(
    colormap_ids: List[ColormapId], existing_colormaps: ColormapsByName, channel_idxs: List[int],
    img_channels: List[ImageChannel]
) -> List[Union[Colormap, None]]:
    colormaps = []
    if len(colormap_ids) == 0:
        colormap_ids = [ColormapEnum.DEFAULT] * len(channel_idxs)
    elif len(colormap_ids) == 1:
        colormap_ids = colormap_ids * len(channel_idxs)

    for i, colormap_id in zip(channel_idxs, colormap_ids):
        colormaps.append(
            parse_colormap_id(
                colormap_id, existing_colormaps, img_channels[i].color
            )
        )
    return colormaps


def parse_colormap_id(
    colormap_id: ColormapId, existing_colormaps: ColormapsByName, default_color: Optional[Color]
) -> Optional[Colormap]:
    """
    Parse a colormap ID to a valid colormap (or None).

    If the parsed ID is a valid colormap which is not registered in the
    existing colormaps, the valid colormap is added to the set of existing ones
    as a side effect.

    Parameters
    ----------
    colormap_id
    existing_colormaps
        Existing colormaps
    default_color
        The color for a monotonic linear colormap if the colormap ID is
        `ColormapEnum.DEFAULT`.

    Returns
    -------
    colormap
        The parsed colormap. If None, no colormap has to be applied.

    Raises
    ------
    ColormapNotFoundProblem
        If the colormap ID cannot be associated to any colormap.
    """
    if colormap_id == ColormapEnum.NONE:
        return None
    elif colormap_id == ColormapEnum.DEFAULT:
        if default_color is None:
            return None
        colormap_id = str(default_color).upper()
    elif colormap_id == ColormapEnum.DEFAULT_INVERTED:
        if default_color is None:
            return existing_colormaps.get('!WHITE')
        colormap_id = '!' + str(default_color).upper()
    else:
        colormap_id = colormap_id.upper()  # noqa

    colormap = existing_colormaps.get(str(colormap_id))
    if colormap is None:
        inverted = colormap_id[0] == "!"
        color = colormap_id[1:] if inverted else colormap_id

        try:
            parsed_color = Color(color)
        except ValueError:
            raise ColormapNotFoundProblem(colormap_id)

        colormap = ColorColormap(parsed_color, inverted=inverted)
        existing_colormaps[colormap.identifier] = colormap
    return colormap
