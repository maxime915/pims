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


def _path_as_dict(path):
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
        data["children"] = [_path_as_dict(p) for p in path.get_extracted_children()]

    return data


def _image_as_dict(image):
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
        "pixel_type": image.pixel_type,
        "significant_bits": image.significant_bits
    }


def _instrument_as_dict(image):
    return {
        "objective": {
            "nominal_magnification": image.objective.get_value("nominal_magnification", None),
            "calibrated_magnification": image.objective.get_value("calibrated_magnification", None)
        },
        "microscope": {
            "model": image.microscope.get_value("model", None)
        }
    }


def _associated_as_dict(image):
    return {
        "has_macro": ("macro" in image.associated),
        "has_thumbnail": ("thumb" in image.associated),
        "has_label": ("label" in image.associated)
    }


def _metadata_as_dict(metadata):
    return {
        "key": metadata.name,
        "value": str(metadata.raw_value),
        "type": metadata.dtype.name
    }


def show_info(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)

    data = _path_as_dict(path)
    if path.is_collection():
        return data

    original = path.get_original()
    check_representation_existence(original)
    data["image"] = _image_as_dict(original)
    data["instrument"] = _instrument_as_dict(original)
    data["associated"] = _associated_as_dict(original)
    data["channels"] = None  # TODO
    data["pyramid"] = None  # TODO
    return data


def show_file(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    return _path_as_dict(path)


def show_image(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _image_as_dict(original)


def show_pyramid(filepath):
    pass


def show_channels(filepath):
    pass


def show_instrument(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _instrument_as_dict(original)


def show_associated(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _associated_as_dict(original)


def show_associated_image(filepath):
    pass


def show_metadata(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)

    data = list()
    stores = [original.core, original.objective, original.microscope,
              original.associated, original.raw_metadata]
    for store in stores:
        for metadata in store.values():
            item = _metadata_as_dict(metadata)
            item.update(dict(namespace=store.namespace))
            data.append(item)

    return response_list(data)
