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

from pims.api.exceptions import check_path_existence, check_path_is_single, \
    check_representation_existence
from pims.api.utils.parameter import filepath2path, path2filepath
from pims.api.utils.response import response_list


def _serialize_path_info(path):
    role = "NONE"
    if path.has_original_role():
        role = "ORIGINAL"
    if path.has_spatial_role():
        role = "SPATIAL"
    if path.has_spectral_role():
        role = "SPECTRAL"
    if path.has_upload_role():
        role = "UPLOAD"

    data = {
        "created_at": path.creation_datetime,
        "extension": path.extension,
        "file_type": "COLLECTION" if path.is_collection() else "SINGLE",
        "filepath": path2filepath(path),
        "is_symbolic": path.is_symlink(),
        "role": role,
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
        "physical_size_x": image.physical_size_x,
        "physical_size_y": image.physical_size_y,
        "physical_size_z": image.physical_size_z,
        "frame_rate": image.frame_rate,
        "acquired_at": image.acquisition_datetime,
        "description": image.description,
        "pixel_type": str(image.pixel_type),
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
    return {
        "has_macro": image.associated.has_macro,
        "has_thumbnail": image.associated.has_thumb,
        "has_label": image.associated.has_label
    }


def _serialize_channels(image):
    return [{
        "index": c.index,
        "emission_wavelength": c.emission_wavelength,
        "excitation_wavelength": c.excitation_wavelength,
        "samples_per_pixel": c.samples_per_pixel,
        "suggested_name": c.suggested_name
    } for c in image.channels]


def _serialize_metadata(metadata):
    return {
        "namespace": metadata.namespace,
        "key": metadata.key,
        "value": str(metadata.raw_value),
        "type": metadata.dtype.name
    }


def show_info(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)

    data = _serialize_path_info(path)
    if path.is_collection():
        return data

    original = path.get_original()
    check_representation_existence(original)
    data["image"] = _serialize_image_info(original)
    data["instrument"] = _serialize_instrument(original)
    data["associated"] = _serialize_associated(original)
    data["channels"] = _serialize_channels(original)
    data["pyramid"] = None  # TODO
    return data


def show_file(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    return _serialize_path_info(path)


def show_image(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _serialize_image_info(original)


def show_pyramid(filepath):
    pass


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


def show_associated_image(filepath):
    pass


def show_metadata(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)

    store = original.raw_metadata
    return response_list([_serialize_metadata(md) for md in store.values()])
