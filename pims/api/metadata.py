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


def info(filepath):
    pass


def file(filepath):
    path = filepath2path(filepath)
    if not path.exists():
        raise FilepathNotFoundProblem(filepath)
    return _path_as_dict(path)


def image(filepath):
    path = filepath2path(filepath)
    if not path.exists():
        raise FilepathNotFoundProblem(filepath)

    if not path.is_single():
        raise NoAppropriateRepresentationProblem(filepath)

    original = path.get_original()
    if not original.exists():
        raise NoAppropriateRepresentationProblem(filepath)

    return _image_as_dict(original)


def pyramid(filepath):
    pass


def channels(filepath):
    pass


def instrument(filepath):
    pass


def associated(filepath):
    pass


def associated_image(filepath):
    pass


def metadata(filepath):
    pass

