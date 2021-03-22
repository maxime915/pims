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

from flask import request, current_app, send_file

from pims.api.exceptions import check_path_existence, check_path_is_single, check_representation_existence
from pims.api.utils.annotation_parameter import parse_annotations, get_annotation_region
from pims.api.utils.header import add_image_size_limit_header
from pims.api.utils.image_parameter import check_zoom_validity, check_level_validity, get_window_output_dimensions, \
    safeguard_output_dimensions, ensure_list
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES
from pims.api.utils.parameter import filepath2path
from pims.processing.annotations import annotation_crop_affine_matrix
from pims.processing.image_response import MaskResponse


def _show_mask(filepath, annotations, context_factor=None,
               length=None, width=None, height=None, zoom=None, level=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    annots = parse_annotations(ensure_list(annotations), ignore_fields=['stroke_width', 'stroke_color'],
                               default={'fill_color': "white"})
    region = get_annotation_region(in_image, annots, context_factor)

    out_format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
    check_zoom_validity(in_image, zoom)
    check_level_validity(in_image, level)
    req_width, req_height = get_window_output_dimensions(in_image, region, height, width, length, zoom,
                                                         level)
    safe_mode = request.headers.get('X-Image-Size-Safety', current_app.config['DEFAULT_IMAGE_SIZE_SAFETY_MODE'])
    out_width, out_height = safeguard_output_dimensions(safe_mode, current_app.config['OUTPUT_SIZE_LIMIT'],
                                                        req_width, req_height)

    affine = annotation_crop_affine_matrix(annots.region, region, out_width, out_height)

    mask_args = {
        "in_image": in_image,
        "annotations": annots,
        "affine_matrix": affine,
        "out_width": out_width,
        "out_height": out_height,
        "out_bitdepth": 8,
        "out_format": out_format
    }

    window = MaskResponse(**mask_args)
    fp = BytesIO(window.get_response_buffer())
    fp.seek(0)

    headers = dict()
    add_image_size_limit_header(headers, req_width, req_height, out_width, out_height)
    return send_file(fp, mimetype=mimetype), headers


def show_mask(filepath, body):
    return _show_mask(filepath, **body)


def show_crop(filepath, body):
    pass


def show_drawing(filepath, body):
    pass


def show_spectra(filepath, body):
    pass


def show_footprint(filepath, body):
    pass


