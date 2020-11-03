from connexion import ProblemException
from flask import current_app

from pims.files.file import Path


class FilepathNotFoundProblem(ProblemException):
    def __init__(self, filepath):
        title = 'Filepath not found'
        detail = 'The file {} does not exist.'.format(filepath)
        type = "problem/resource-not-found"
        super(FilepathNotFoundProblem, self).__init__(status=404, title=title, detail=detail, type=type)
        
        
def filepath2path(filepath):
    return Path(current_app.config['FILE_ROOT_PATH'], filepath)


def path2filepath(path):
    root = current_app.config['FILE_ROOT_PATH']
    if root[-1] != "/":
        root += "/"
    return str(path).replace(root, "")


def _path_as_dict(path):
    roles = []
    if path.has_original_role():
        roles.append("ORIGINAL")
    if path.has_spatial_role():
        roles.append("SPATIAL")
    if path.has_spectral_role():
        roles.append("SPECTRAL")

    return {
        "created_at": path.creation_datetime,
        "extension": path.extension,
        "file_type": "COLLECTION" if path.is_collection() else "SINGLE",
        "filepath": path2filepath(path),
        "is_symbolic": path.is_symlink(),
        "roles": roles,
        "size": path.size,
        "stem": path.true_stem
    }


def info(filepath):
    pass


def file(filepath):
    path = filepath2path(filepath)
    if not path.exists():
        raise FilepathNotFoundProblem(filepath)
    return _path_as_dict(path)


def image(filepath):
    pass


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

