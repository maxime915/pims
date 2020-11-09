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
from flask import current_app


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
