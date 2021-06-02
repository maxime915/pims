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
from pims.api.utils.models import AnnotationStyleMode
from pims.api.utils.parameter import filepath2path
from pims.api.window import show_window
from pims.processing.annotations import annotation_crop_affine_matrix
from pims.processing.image_response import MaskResponse


def _show_mask(filepath, annotations, context_factor=None,
               length=None, width=None, height=None, zoom=None, level=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    origin = request.headers.get('X-Annotation-Origin', current_app.config['DEFAULT_ANNOTATION_ORIGIN'])
    annots = parse_annotations(ensure_list(annotations), ignore_fields=['stroke_width', 'stroke_color'],
                               default={'fill_color': "white"}, origin=origin, im_height=in_image.height)
    region = get_annotation_region(in_image, annots, context_factor)

    out_format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
    check_zoom_validity(in_image.pyramid, zoom)
    check_level_validity(in_image.pyramid, level)
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


def _show_crop(filepath, annotations, context_factor=None, background_transparency=None,
               length=None, width=None, height=None, zoom=None, level=None,
               channels=None, z_slices=None, timepoints=None,
               c_reduction="ADD", z_reduction=None, t_reduction=None,
               min_intensities=None, max_intensities=None, colormaps=None, filters=None,
               gammas=None, log=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    origin = request.headers.get('X-Annotation-Origin', current_app.config['DEFAULT_ANNOTATION_ORIGIN'])
    annots = parse_annotations(ensure_list(annotations), ignore_fields=['stroke_width', 'stroke_color'],
                               default={'fill_color': "white"}, origin=origin, im_height=in_image.height)
    region = get_annotation_region(in_image, annots, context_factor)

    annot_style = {
        "mode": AnnotationStyleMode.CROP,
        "background_transparency": background_transparency
    }

    return show_window(filepath, region, length=length, width=width, height=height, zoom=zoom,
                       level=level, channels=channels, z_slices=z_slices, timepoints=timepoints,
                       c_reduction=c_reduction, z_reduction=z_reduction, t_reduction=t_reduction,
                       min_intensities=min_intensities, max_intensities=max_intensities, colormaps=colormaps,
                       filters=filters, gammas=gammas, log=log, annotations=annots, annotation_style=annot_style,
                       bits=8, colorspace='AUTO')


def show_crop(filepath, body):
    return _show_crop(filepath, **body)


def _show_drawing(filepath, annotations, context_factor=None,
                  try_square=None, point_cross=None, point_envelope_length=None,
                  length=None, width=None, height=None, zoom=None, level=None,
                  channels=None, z_slices=None, timepoints=None,
                  c_reduction="ADD", z_reduction=None, t_reduction=None,
                  min_intensities=None, max_intensities=None, colormaps=None, filters=None,
                  gammas=None, log=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    origin = request.headers.get('X-Annotation-Origin', current_app.config['DEFAULT_ANNOTATION_ORIGIN'])
    annots = parse_annotations(ensure_list(annotations), ignore_fields=['fill_color'],
                               default={'stroke_color': "red", 'stroke_width': 1},
                               point_envelope_length=point_envelope_length, origin=origin, im_height=in_image.height)
    region = get_annotation_region(in_image, annots, context_factor, try_square)

    annot_style = {
        "mode": AnnotationStyleMode.DRAWING,
        "point_cross": point_cross,
        "point_envelope_length": point_envelope_length
    }

    return show_window(filepath, region, length=length, width=width, height=height, zoom=zoom,
                       level=level, channels=channels, z_slices=z_slices, timepoints=timepoints,
                       c_reduction=c_reduction, z_reduction=z_reduction, t_reduction=t_reduction,
                       min_intensities=min_intensities, max_intensities=max_intensities, colormaps=colormaps,
                       filters=filters, gammas=gammas, log=log, annotations=annots, annotation_style=annot_style,
                       bits=8, colorspace='AUTO')


def show_drawing(filepath, body):
    return _show_drawing(filepath, **body)


def show_spectra(filepath, body):
    pass


def show_footprint(filepath, body):
    pass
