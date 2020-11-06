from pims.api.exceptions import FilepathNotFoundProblem, NoAppropriateRepresentationProblem
from pims.api.utils import filepath2path, path2filepath


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


def check_path_existence(path):
    if not path.exists():
        raise FilepathNotFoundProblem(path)


def check_path_is_single(path):
    if not path.is_single():
        raise NoAppropriateRepresentationProblem(path)


def check_representation_existence(path):
    if not path.exists():
        raise NoAppropriateRepresentationProblem(path)


def info(filepath):
    pass


def file(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    return _path_as_dict(path)


def image(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _image_as_dict(original)


def pyramid(filepath):
    pass


def channels(filepath):
    pass


def instrument(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _instrument_as_dict(original)


def associated(filepath):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    original = path.get_original()
    check_representation_existence(original)
    return _associated_as_dict(original)


def associated_image(filepath):
    pass


def metadata(filepath):
    pass

