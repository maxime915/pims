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

from connexion.exceptions import UnsupportedMediaTypeProblem
from flask import current_app

PNG_MIMETYPES = {
    "image/png": "PNG",
}

WEBP_MIMETYPES = {
    "image/webp": "WEBP"
}

JPEG_MIMETYPES = {
    "image/jpg": "JPEG",
    "image/jpeg": "JPEG"
}

SUPPORTED_MIMETYPES = dict()
SUPPORTED_MIMETYPES.update(PNG_MIMETYPES)
SUPPORTED_MIMETYPES.update(JPEG_MIMETYPES)
SUPPORTED_MIMETYPES.update(WEBP_MIMETYPES)


def mimetype_to_mpl_slug(mimetype):
    """
    Return the format slug identifier used by Matplotlib for the given mime type.

    Matplotlib format slugs are: png, jpg, jpeg, ...
    See https://matplotlib.org/3.1.1/api/_as_gen/matplotlib.pyplot.savefig.html
    """
    if mimetype not in SUPPORTED_MIMETYPES.keys():
        raise UnsupportedMediaTypeProblem()

    return SUPPORTED_MIMETYPES[mimetype].lower()


def filepath2path(filepath):
    """
    Transform a relative filepath to a path.

    Parameters
    ----------
    filepath: str
        Relative filepath

    Returns
    -------
    path: Path
        Absolute resolved path
    """
    from pims.files.file import Path
    return Path(current_app.config['FILE_ROOT_PATH'], filepath)


def path2filepath(path):
    """
    Transform an absolute path to a relative filepath.

    Parameters
    ----------
    path: Path
        Absolute resolved path

    Returns
    -------
    filepath: str
        Relative filepath
    """
    root = current_app.config['FILE_ROOT_PATH']
    if root[-1] != "/":
        root += "/"
    return str(path).replace(root, "")