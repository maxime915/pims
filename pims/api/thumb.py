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

from connexion import NoContent, request
from flask import send_file

from pims.api.exceptions import check_path_existence, check_path_is_single, check_representation_existence
from pims.api.utils.image_parameter import get_output_dimensions, get_channel_planes, \
    get_z_slice_planes, get_timepoint_planes, check_array_size, ensure_list
from pims.api.utils.mimetype import get_output_format
from pims.api.utils.parameter import filepath2path
from pims.processing.window import Thumbnail


def show_thumb(filepath, channels=None, z_slices=None, timepoints=None,
               c_reduction=None, z_reduction=None, t_reduction=None,
               width=None, height=None, length=None,
               min_intensities=None, max_intensities=None, colormaps=None, filters=None,
               gammas=None, log=None, use_precomputed=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)
    image = path.get_spatial()
    check_representation_existence(image)

    out_format, mimetype = get_output_format(request)
    if not out_format:
        return NoContent, 406

    out_width, out_height = get_output_dimensions(image, height, width, length)

    channels, z_slices, timepoints = ensure_list(channels), ensure_list(z_slices), ensure_list(timepoints)
    min_intensities, max_intensities = ensure_list(min_intensities), ensure_list(max_intensities)
    colormaps, filters, gammas = ensure_list(colormaps), ensure_list(filters), ensure_list(gammas)

    channels, c_reduction = get_channel_planes(image, channels, c_reduction)
    z_slices, z_reduction = get_z_slice_planes(image, z_slices, z_reduction)
    timepoints, t_reduction = get_timepoint_planes(image, timepoints, t_reduction)

    check_array_size(gammas, allowed=[1, len(channels)], nullable=True)
    check_array_size(filters, allowed=[1, len(channels)], nullable=True)
    check_array_size(colormaps, allowed=[1, len(channels)], nullable=True)
    check_array_size(min_intensities, allowed=[1, len(channels)], nullable=True)
    check_array_size(max_intensities, allowed=[1, len(channels)], nullable=True)

    thumb = Thumbnail(image, out_width, out_height, out_format, log, use_precomputed, gammas)
    fp = BytesIO(thumb.get_processed_buffer())
    fp.seek(0)
    return send_file(fp, mimetype=mimetype)


def show_thumb_with_body(filepath, body):
    pass

