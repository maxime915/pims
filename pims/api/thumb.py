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
from io import BytesIO

from connexion import request
from flask import send_file, current_app

from pims.api.exceptions import check_path_existence, check_path_is_single, check_representation_existence
from pims.api.utils.image_parameter import get_output_dimensions, get_channel_indexes, \
    get_zslice_indexes, get_timepoint_indexes, check_array_size, ensure_list, check_reduction_validity, \
    safeguard_output_dimensions
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES
from pims.api.utils.parameter import filepath2path
from pims.api.utils.header import add_image_size_limit_header
from pims.processing.image_response import ThumbnailResponse


def show_thumb(filepath, channels=None, z_slices=None, timepoints=None,
               c_reduction="ADD", z_reduction=None, t_reduction=None,
               width=None, height=None, length=None,
               min_intensities=None, max_intensities=None, colormaps=None, filters=None,
               gammas=None, log=None, use_precomputed=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    out_format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
    req_width, req_height = get_output_dimensions(in_image, height, width, length)
    safe_mode = request.headers.get('X-Image-Size-Safety', current_app.config['DEFAULT_IMAGE_SIZE_SAFETY_MODE'])
    out_width, out_height = safeguard_output_dimensions(safe_mode, current_app.config['OUTPUT_SIZE_LIMIT'],
                                                        req_width, req_height)

    channels, z_slices, timepoints = ensure_list(channels), ensure_list(z_slices), ensure_list(timepoints)
    min_intensities, max_intensities = ensure_list(min_intensities), ensure_list(max_intensities)
    colormaps, filters, gammas = ensure_list(colormaps), ensure_list(filters), ensure_list(gammas)

    channels = get_channel_indexes(in_image, channels)
    check_reduction_validity(channels, c_reduction, 'channels')
    z_slices = get_zslice_indexes(in_image, z_slices)
    check_reduction_validity(z_slices, z_reduction, 'z_slices')
    timepoints = get_timepoint_indexes(in_image, timepoints)
    check_reduction_validity(timepoints, t_reduction, 'timepoints')

    array_parameters = (gammas, filters, colormaps, max_intensities, max_intensities)
    for array_parameter in array_parameters:
        # check_array_size(array_parameter, allowed=[1, len(channels)], nullable=True)
        # Currently, we only allow 1 parameter to be applied to all channels
        check_array_size(array_parameter, allowed=[1], nullable=True)

    # TODO: verify maximum allowed values for min_intensities
    # TODO: verify maximum allowed values for max_intensities
    # TODO: verify colormap names are valid
    # TODO: verify filter names are valid

    thumb_args = {
        "in_image": in_image,
        "channels": channels,
        "z_slices": z_slices,
        "timepoints": timepoints,
        "c_reduction": c_reduction,
        "z_reduction": z_reduction,
        "t_reduction": t_reduction,
        "out_width": out_width,
        "out_height": out_height,
        "out_format": out_format,
        "gammas": gammas,
        "filters": filters,
        "colormaps": colormaps,
        "min_intensities": min_intensities,
        "max_intensities": max_intensities,
        "log": log,
        "use_precomputed": use_precomputed
    }
    thumb = ThumbnailResponse(**thumb_args)
    fp = BytesIO(thumb.get_response_buffer())
    fp.seek(0)

    headers = dict()
    add_image_size_limit_header(headers, req_width, req_height, out_width, out_height)
    return send_file(fp, mimetype=mimetype), headers


def show_thumb_with_body(filepath, body):
    return show_thumb(filepath, **body)

