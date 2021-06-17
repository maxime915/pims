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
from typing import Union, List

from fastapi import APIRouter, Depends

from pims.api.exceptions import check_representation_existence
from pims.api.utils.annotation_parameter import parse_annotations
from pims.api.utils.header import add_image_size_limit_header, ImageAnnotationRequestHeaders
from pims.api.utils.image_parameter import get_channel_indexes, \
    get_zslice_indexes, get_timepoint_indexes, check_array_size, ensure_list, check_reduction_validity, \
    safeguard_output_dimensions, parse_intensity_bounds, check_zoom_validity, check_level_validity, parse_bitdepth, \
    parse_region, check_tileindex_validity, check_tilecoord_validity, get_window_output_dimensions, parse_filter_ids
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES, OutputExtension, \
    extension_path_parameter
from pims.api.utils.models import WindowRequest, AnnotationStyleMode, TierIndexType
from pims.api.utils.parameter import imagepath_parameter
from pims.config import get_settings, Settings
from pims.files.file import Path
from pims.filters import FILTERS
from pims.processing.annotations import annotation_crop_affine_matrix, ParsedAnnotations
from pims.processing.image_response import WindowResponse, MaskResponse
from pims.processing.region import Region

router = APIRouter()
api_tags = ['Windows']


@router.post('/image/{filepath:path}/window{extension:path}', tags=api_tags)
def show_window_with_body(
        body: WindowRequest,
        path: Path = Depends(imagepath_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        headers: ImageAnnotationRequestHeaders = Depends(),
        config: Settings = Depends(get_settings)
):
    """
    **`GET with body` - when a GET with URL encoded query parameters is not possible due to URL size limits, a POST
    with body content must be used.**

    Get a window (rectangular crop) extract from an image, with given channels, focal
    planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
     tile is extracted from the median focal plane at first timepoint.
    """
    return _show_window(path, **body.dict(), extension=extension, headers=headers, config=config)


def _show_window(
        path: Path,
        region: Union[Region, dict],
        height, width, length, zoom, level,
        channels, z_slices, timepoints,
        min_intensities, max_intensities, filters, gammas,
        bits, colorspace,
        annotations: Union[ParsedAnnotations, dict, List[dict]],
        annotation_style: dict,
        extension,
        headers,
        config: Settings,
        colormaps=None, c_reduction="ADD", z_reduction=None, t_reduction=None
):
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    if not isinstance(region, Region):
        tier_index_type = region['tier_index_type']
        reference_tier_index = region['reference_tier_index']
        if reference_tier_index is None:
            if tier_index_type == TierIndexType.LEVEL:
                reference_tier_index = 0
            else:
                reference_tier_index = in_image.pyramid.max_zoom

        if 'top' in region:
            # Parse raw WindowRegion to Region
            region = parse_region(in_image, region['top'], region['left'],
                                  region['width'], region['height'],
                                  reference_tier_index, tier_index_type,
                                  silent_oob=False)
        elif 'ti' in region:
            # Parse raw WindowTileIndex region to Region
            check_tileindex_validity(in_image.pyramid, region['ti'],
                                     reference_tier_index, tier_index_type)
            region = in_image.pyramid.get_tier_at(reference_tier_index,
                                                  tier_index_type).ti2region(region['ti'])
        elif ('tx', 'ty') in region:
            # Parse raw WindowTileCoord region to Region
            check_tilecoord_validity(in_image.pyramid, region['tx'], region['ty'],
                                     reference_tier_index, tier_index_type)
            region = in_image.pyramid.get_tier_at(reference_tier_index,
                                                  tier_index_type).txty2region(region['tx'], region['ty'])

    out_format, mimetype = get_output_format(extension, headers.accept, VISUALISATION_MIMETYPES)
    check_zoom_validity(in_image.pyramid, zoom)
    check_level_validity(in_image.pyramid, level)
    req_size = get_window_output_dimensions(in_image, region, height, width, length, zoom, level)
    out_size = safeguard_output_dimensions(headers.safe_mode, config.output_size_limit, *req_size)
    out_width, out_height = out_size

    channels = ensure_list(channels)
    z_slices = ensure_list(z_slices)
    timepoints = ensure_list(timepoints)

    channels = get_channel_indexes(in_image, channels)
    check_reduction_validity(channels, c_reduction, 'channels')
    z_slices = get_zslice_indexes(in_image, z_slices)
    check_reduction_validity(z_slices, z_reduction, 'z_slices')
    timepoints = get_timepoint_indexes(in_image, timepoints)
    check_reduction_validity(timepoints, t_reduction, 'timepoints')

    min_intensities = ensure_list(min_intensities)
    max_intensities = ensure_list(max_intensities)
    colormaps = ensure_list(colormaps)
    filters = ensure_list(filters)
    gammas = ensure_list(gammas)

    array_parameters = (min_intensities, max_intensities)
    for array_parameter in array_parameters:
        check_array_size(array_parameter, allowed=[0, 1, len(channels)], nullable=False)
    intensities = parse_intensity_bounds(in_image, channels, min_intensities, max_intensities)
    min_intensities, max_intensities = intensities

    array_parameters = (gammas, filters, colormaps)
    for array_parameter in array_parameters:
        # Currently, we only allow 1 parameter to be applied to all channels
        check_array_size(array_parameter, allowed=[0, 1], nullable=False)
    filters = parse_filter_ids(filters, FILTERS)

    out_bitdepth = parse_bitdepth(in_image, bits)

    # TODO: verify colormap names are valid

    if annotations and annotation_style and not isinstance(annotations, ParsedAnnotations):
        if annotation_style['mode'] == AnnotationStyleMode.DRAWING:
            ignore_fields = ['fill_color']
            default = {'stroke_color': (255, 0, 0), 'stroke_width': 1}
            point_envelope_length = annotation_style['point_envelope_length']
        else:
            ignore_fields = ['stroke_width', 'stroke_color']
            default = {'fill_color': (255, 255, 255)}
            point_envelope_length = None

        annotations = parse_annotations(
            ensure_list(annotations), ignore_fields,
            default, point_envelope_length,
            origin=headers.annot_origin, im_height=in_image.height
        )

    affine = None
    if annotations:
        affine = annotation_crop_affine_matrix(annotations.region, region, *out_size)

    if annotations and annotation_style and \
            annotation_style['mode'] == AnnotationStyleMode.MASK:
        window = MaskResponse(
            in_image,
            annotations, affine,
            out_width, out_height, out_bitdepth, out_format
        )
    else:
        window = WindowResponse(
            in_image, channels, z_slices, timepoints,
            region, out_format, out_width, out_height,
            c_reduction, z_reduction, t_reduction,
            gammas, filters, colormaps,
            min_intensities, max_intensities, False,
            out_bitdepth, colorspace,
            annotations, affine, annotation_style
        )

    return window.http_response(
        mimetype,
        extra_headers=add_image_size_limit_header(dict(), *req_size, *out_size)
    )
