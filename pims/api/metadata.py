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

from flask import current_app, send_file
from connexion import request

from pims.api.exceptions import check_path_existence, check_path_is_single, \
    check_representation_existence, NoAppropriateRepresentationProblem
from pims.api.utils.header import add_image_size_limit_header
from pims.api.utils.image_parameter import get_output_dimensions, safeguard_output_dimensions
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES
from pims.api.utils.parameter import filepath2path, path2filepath
from pims.api.utils.response import response_list, convert_quantity
from pims.formats.utils.metadata import MetadataType
from pims.processing.image_response import AssociatedResponse


def _serialize_path_role(path):
    role = "NONE"
    if path.has_original_role():
        role = "ORIGINAL"
    if path.has_spatial_role():
        role = "SPATIAL"
    if path.has_spectral_role():
        role = "SPECTRAL"
    if path.has_upload_role():
        role = "UPLOAD"
    return role


def _serialize_path_info(path):
    data = {
        "created_at": path.creation_datetime,
        "extension": path.extension,
        "file_type": "COLLECTION" if path.is_collection() else "SINGLE",
        "filepath": path2filepath(path),
        "is_symbolic": path.is_symlink(),
        "role": _serialize_path_role(path),
        "size": path.size,
        "stem": path.true_stem
    }

    if path.is_collection():
        data["children"] = [_serialize_path_info(p) for p in path.get_extracted_children()]

    return data


def _serialize_image_info(image):
    return {
        "original_format": image.format.get_identifier(),
        "width": image.width,
        "height": image.height,
        "depth": image.depth,
        "duration": image.duration,
        "n_channels": image.n_channels,
        "physical_size_x": convert_quantity(image.physical_size_x, "micrometers"),
        "physical_size_y": convert_quantity(image.physical_size_y, "micrometers"),
        "physical_size_z": convert_quantity(image.physical_size_z, "micrometers"),
        "frame_rate": image.frame_rate,
        "acquired_at": image.acquisition_datetime,
        "description": image.description,
        "pixel_type": image.pixel_type,
        "significant_bits": image.significant_bits
    }


def _serialize_instrument(image):
    return {
        "objective": {
            "nominal_magnification": image.objective.nominal_magnification,
            "calibrated_magnification": image.objective.calibrated_magnification
        },
        "microscope": {
            "model": image.microscope.model
        }
    }


def _serialize_associated(image):
    return [
        {
            "name": associated._kind,
            "width": associated.width,
            "height": associated.height,
            "n_channels": associated.n_channels
        } for associated in (image.associated_thumb, image.associated_label, image.associated_macro)
        if associated.exists
    ]


def _serialize_channels(image):
    return [{
        "index": c.index,
        "emission_wavelength": c.emission_wavelength,
        "excitation_wavelength": c.excitation_wavelength,
        "suggested_name": c.suggested_name
    } for c in image.channels]


def _serialize_metadata(metadata):
    return {
        "namespace": metadata.namespace,
        "key": metadata.key,
        "value": metadata.value if metadata.metadata_type != MetadataType.UNKNOWN else str(metadata.value),
        "type": metadata.metadata_type
    }


def _serialize_pyramid(pyramid):
    if pyramid is None:
        return None

    def _serialize_tier(tier):
        return {
            "width": tier.width,
            "height": tier.height,
            "level": tier.level,
            "zoom": tier.zoom,
            "tile_width": tier.tile_width,
            "tile_height": tier.tile_height,
            "downsampling_factor": tier.width_factor
        }

    return {
        "n_tiers": pyramid.n_levels,
        "tiers": [_serialize_tier(tier) for tier in pyramid]
    }


def _serialize_representation(path):
    data = {
        "role": _serialize_path_role(path),
        "file": _serialize_path_info(path)
    }

    if path.has_spatial_role() or path.has_spectral_role():
        data["pyramid"] = _serialize_pyramid(path.pyramid)

    return data


def show_file(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    return _serialize_path_info(path)


def show_info(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    data = dict()
    data["image"] = _serialize_image_info(original)
    data["instrument"] = _serialize_instrument(original)
    data["associated"] = _serialize_associated(original)
    data["channels"] = _serialize_channels(original)
    data["representations"] = [_serialize_representation(rpr) for rpr in original.get_representations()]
    return data


def show_image(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _serialize_image_info(original)


def show_channels(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return response_list(_serialize_channels(original))


def show_instrument(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _serialize_instrument(original)


def show_associated(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _serialize_associated(original)


def show_associated_image(filepath, associated_key, length=None, width=None, height=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    associated = None
    if associated_key in ('thumb', 'label', 'macro'):
        associated = getattr(in_image, 'associated_{}'.format(associated_key))

    if not associated or not associated.exists:
        raise NoAppropriateRepresentationProblem(filepath, associated_key)

    out_format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
    req_width, req_height = get_output_dimensions(associated, height, width, length)
    safe_mode = request.headers.get('X-Image-Size-Safety', current_app.config['DEFAULT_IMAGE_SIZE_SAFETY_MODE'])
    out_width, out_height = safeguard_output_dimensions(safe_mode, current_app.config['OUTPUT_SIZE_LIMIT'],
                                                        req_width, req_height)

    thumb = AssociatedResponse(in_image, associated_key, out_width, out_height, out_format)
    fp = BytesIO(thumb.get_processed_buffer())
    fp.seek(0)

    headers = dict()
    add_image_size_limit_header(headers, req_width, req_height, out_width, out_height)
    return send_file(fp, mimetype=mimetype), headers


def show_metadata(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)

    store = original.raw_metadata
    return response_list([_serialize_metadata(md) for md in store.values()])


def list_representations(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    return response_list([_serialize_representation(rpr) for rpr in path.get_representations()])


def show_representation(filepath, representation):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    rpr = path.get_representation(representation)
    return _serialize_representation(rpr)
