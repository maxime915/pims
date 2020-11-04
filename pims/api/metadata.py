from connexion import ProblemException
from flask import current_app

from pims.files.file import Path


class FilepathNotFoundProblem(ProblemException):
    def __init__(self, filepath):
        title = 'Filepath not found'
        detail = 'The file {} does not exist.'.format(filepath)
        type = "problem/resource-not-found"
        super(FilepathNotFoundProblem, self).__init__(status=404, title=title, detail=detail, type=type)


class FilepathRepresentationNotFoundProblem(ProblemException):
    def __init__(self, filepath):
        title = 'No appropriate representation found for this filepath'
        detail = 'The file {} does not have an appropriate representation.'.format(filepath)
        type = "problem/resource-not-found"
        super(FilepathRepresentationNotFoundProblem, self).__init__(status=404, title=title, detail=detail, type=type)
        
        
def filepath2path(filepath):
    return Path(current_app.config['FILE_ROOT_PATH'], filepath)


def path2filepath(path):
    root = current_app.config['FILE_ROOT_PATH']
    if root[-1] != "/":
        root += "/"
    return str(path).replace(root, "")


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
        raise FilepathRepresentationNotFoundProblem(filepath)

    original = path.get_original()
    if not original.exists():
        raise FilepathRepresentationNotFoundProblem(filepath)

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

