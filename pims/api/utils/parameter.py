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
from fastapi.params import Path as PathParam


from pims.config import get_settings


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
    config = get_settings()
    return Path(config.root, filepath)


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
    config = get_settings()
    root = config.root
    if root[-1] != "/":
        root += "/"
    return str(path).replace(root, "")


def filepath_parameter(
    filepath: str = PathParam(
        ..., description="The file path, relative to server base path.",
        example='123/my-file.ext'
    )
):
    path = filepath2path(filepath)
    if not path.exists():
        from pims.api.exceptions import FilepathNotFoundProblem
        raise FilepathNotFoundProblem(path)
    return path


def imagepath_parameter(
    filepath: str = PathParam(
        ..., description="The file path, relative to server base path.",
        example='123/my-file.ext'
    )
):
    path = filepath2path(filepath)
    if not path.exists():
        from pims.api.exceptions import FilepathNotFoundProblem
        raise FilepathNotFoundProblem(path)
    if not path.is_single():
        from pims.api.exceptions import NoAppropriateRepresentationProblem
        raise NoAppropriateRepresentationProblem(path)
    return path
