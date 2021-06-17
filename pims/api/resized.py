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

from fastapi import APIRouter, Depends

from pims.api.exceptions import check_representation_existence
from pims.api.utils.header import add_image_size_limit_header, ImageRequestHeaders
from pims.api.utils.image_parameter import get_thumb_output_dimensions, get_channel_indexes, \
    get_zslice_indexes, get_timepoint_indexes, check_array_size, ensure_list, check_reduction_validity, \
    safeguard_output_dimensions, parse_intensity_bounds, check_zoom_validity, check_level_validity, parse_bitdepth, \
    parse_filter_ids
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES, OutputExtension, \
    extension_path_parameter
from pims.api.utils.models import PlaneSelectionQueryParams, ResizedRequest, ImageOutDisplayQueryParams, \
    ImageOutProcessingQueryParams, ImageOpsProcessingQueryParams
from pims.api.utils.parameter import imagepath_parameter
from pims.config import Settings, get_settings
from pims.files.file import Path
from pims.filters import FILTERS
from pims.processing.image_response import ResizedResponse

router = APIRouter()
api_tags = ['Resized']


@router.get('/image/{filepath:path}/resized{extension:path}', tags=api_tags)
def show_resized(
        path: Path = Depends(imagepath_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        output: ImageOutDisplayQueryParams = Depends(),
        output2: ImageOutProcessingQueryParams = Depends(),
        planes: PlaneSelectionQueryParams = Depends(),
        operations: ImageOpsProcessingQueryParams = Depends(),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings)
):
    """
    Get a resized full image (thumbnail), with given channels, focal planes and timepoints. If
    multiple channels are given (slice or selection), they are merged. If multiple focal planes or timepoints are
    given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
    thumbnail is extracted from the median focal plane at first timepoint.

    **While `/image/{filepath}/thumb` provides optimization for visualisation, this endpoint has a general purpose,
    such as computer vision, image processing or machine learning.**
    """
    return _show_resized(
        path=path, **output.dict(), **output2.dict(), **planes.dict(), **operations.dict(),
        extension=extension, headers=headers, config=config
    )


@router.post('/image/{filepath:path}/resized{extension:path}', tags=api_tags)
def show_resized_with_body(
        body: ResizedRequest,
        path: Path = Depends(imagepath_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings)
):
    """
    **`GET with body` - when a GET with URL encoded query parameters is not possible due to URL size limits, a POST
    with body content must be used.**

    Get a resized full image (thumbnail), with given channels, focal planes and timepoints. If
    multiple channels are given (slice or selection), they are merged. If multiple focal planes or timepoints are
    given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
    thumbnail is extracted from the median focal plane at first timepoint.

    **While `/image/{filepath}/thumb` provides optimization for visualisation, this endpoint has a general purpose,
    such as computer vision, image processing or machine learning.**
    """
    return _show_resized(path, **body.dict(), extension=extension, headers=headers, config=config)


def _show_resized(
        path: Path,
        height, width, length, zoom, level,
        channels, z_slices, timepoints,
        min_intensities, max_intensities, filters, gammas,
        bits, colorspace,
        extension,
        headers,
        config: Settings,
        colormaps=None, c_reduction="ADD", z_reduction=None, t_reduction=None
):
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    out_format, mimetype = get_output_format(extension, headers.accept, VISUALISATION_MIMETYPES)
    check_zoom_validity(in_image.pyramid, zoom)
    check_level_validity(in_image.pyramid, level)
    req_size = get_thumb_output_dimensions(in_image, height, width, length, zoom, level)
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

    return ResizedResponse(
        in_image, channels, z_slices, timepoints,
        out_format, out_width, out_height,
        c_reduction, z_reduction, t_reduction,
        gammas, filters, colormaps, min_intensities, max_intensities,
        False, out_bitdepth, colorspace
    ).http_response(
        mimetype,
        extra_headers=add_image_size_limit_header(dict(), *req_size, *out_size)
    )
