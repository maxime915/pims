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
from pims.api.utils.annotation_parameter import parse_annotations
from pims.api.utils.image_parameter import get_channel_indexes, \
    get_zslice_indexes, get_timepoint_indexes, check_array_size, ensure_list, check_reduction_validity, \
    safeguard_output_dimensions, parse_intensity_bounds, check_zoom_validity, check_level_validity, parse_bitdepth, \
    parse_region, check_tileindex_validity, check_tilecoord_validity, get_window_output_dimensions
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES
from pims.api.utils.parameter import filepath2path
from pims.api.utils.header import add_image_size_limit_header
from pims.processing.annotations import AnnotationList, annotation_crop_affine_matrix
from pims.processing.image_response import WindowResponse, MaskResponse
from pims.processing.region import Region


def show_window(filepath, region=None, tx=None, ty=None, ti=None, reference_tier_index=None, tier_index_type=None,
                width=None, height=None, length=None, zoom=None, level=None,
                channels=None, z_slices=None, timepoints=None,
                c_reduction="ADD", z_reduction=None, t_reduction=None,
                min_intensities=None, max_intensities=None, colormaps=None, filters=None,
                gammas=None, log=None, bits=None, colorspace=None,
                annotations=None, annotation_style=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    if reference_tier_index is None:
        reference_tier_index = 0 if tier_index_type == "LEVEL" else in_image.pyramid.max_zoom

    if region is not None and type(region) == dict:
        region = parse_region(in_image, region, reference_tier_index, tier_index_type, silent_oob=False)
    elif ti is not None:
        check_tileindex_validity(in_image.pyramid, ti, reference_tier_index, tier_index_type)
        region = in_image.pyramid.get_tier_at(reference_tier_index, tier_index_type).ti2region(ti)
    elif tx and ty is not None:
        check_tilecoord_validity(in_image.pyramid, tx, ty, reference_tier_index, tier_index_type)
        region = in_image.pyramid.get_tier_at(reference_tier_index, tier_index_type).txty2region(tx, ty)
    elif type(region) != Region:
        # should not happen as this case is already handled by connexion.
        return

    out_format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
    check_zoom_validity(in_image.pyramid, zoom)
    check_level_validity(in_image.pyramid, level)
    req_width, req_height = get_window_output_dimensions(in_image, region, height, width, length, zoom,
                                                         level)
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

    array_parameters = (min_intensities, max_intensities)
    for array_parameter in array_parameters:
        check_array_size(array_parameter, allowed=[0, 1, len(channels)], nullable=False)
    min_intensities, max_intensities = parse_intensity_bounds(in_image, channels, min_intensities, max_intensities)

    array_parameters = (gammas, filters, colormaps)
    for array_parameter in array_parameters:
        # Currently, we only allow 1 parameter to be applied to all channels
        check_array_size(array_parameter, allowed=[0, 1], nullable=False)

    out_bitdepth = parse_bitdepth(in_image, bits)

    # TODO: verify colormap names are valid
    # TODO: verify filter names are valid

    if annotations and annotation_style and not isinstance(annotations, AnnotationList):
        if annotation_style['mode'] == 'DRAWING':
            ignore_fields = ['fill_color']
            default = {'stroke_color': "red", 'stroke_width': 1}
            point_envelope_length = annotation_style.get('point_envelope_length')
        else:
            ignore_fields = ['stroke_width', 'stroke_color']
            default = {'fill_color': "white"}
            point_envelope_length = None

        annotations = parse_annotations(ensure_list(annotations), ignore_fields,
                                        default, point_envelope_length)

    affine = None
    if annotations:
        affine = annotation_crop_affine_matrix(annotations.region, region, out_width, out_height)

    window_args = {
        "in_image": in_image,
        "in_channels": channels,
        "in_z_slices": z_slices,
        "in_timepoints": timepoints,
        "region": region,
        "c_reduction": c_reduction,
        "z_reduction": z_reduction,
        "t_reduction": t_reduction,
        "out_width": out_width,
        "out_height": out_height,
        "out_format": out_format,
        "out_bitdepth": out_bitdepth,
        "gammas": gammas,
        "filters": filters,
        "colormaps": colormaps,
        "min_intensities": min_intensities,
        "max_intensities": max_intensities,
        "log": log,
        "colorspace": colorspace,
        "annotations": annotations,
        "annot_params": annotation_style,
        "affine_matrix": affine
    }

    if annotations and annotation_style is not None and annotation_style['mode'] == 'MASK':
        window = MaskResponse(**window_args)
    else:
        window = WindowResponse(**window_args)
    fp = BytesIO(window.get_response_buffer())
    fp.seek(0)

    headers = dict()
    add_image_size_limit_header(headers, req_width, req_height, out_width, out_height)
    return send_file(fp, mimetype=mimetype), headers


def show_window_with_body(filepath, body):
    return show_window(filepath, **body)
