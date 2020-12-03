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
import os

import pytest

from pims.api.utils.parameter import filepath2path, path2filepath
from pims.api.utils.response import response_list
from pims.files.file import Path


def test_response_list():
    items = list()
    resp = response_list(items)
    assert resp == dict(items=[], size=0)

    items = ["a", "b"]
    resp = response_list(items)
    assert resp == dict(items=items, size=len(items))


@pytest.mark.parametrize("filepath", ("/abc", "abc", "abc/foo"))
def test_filepath2path(app, filepath):
    with app.app_context():
        assert str(filepath2path(filepath)) == os.path.join(app.config["FILE_ROOT_PATH"], filepath)


@pytest.mark.parametrize("rootpath", ("/abc", "abc", "abc/foo/"))
def test_path2filepath(app, rootpath):
    with app.app_context():
        true_root = app.config["FILE_ROOT_PATH"]
        app.config["FILE_ROOT_PATH"] = rootpath
        path = Path(rootpath) / "dir/file"
        assert path2filepath(path) == "dir/file"
        app.config["FILE_ROOT_PATH"] = true_root
