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
import shutil
from pathlib import Path

import pytest
from flask import current_app
from contextlib import contextmanager

from pims.app import create_app


with open(os.path.join(os.path.dirname(__file__), 'fake_files.csv'), 'r') as f:
    lines = f.read().splitlines()
    _fake_files = dict()
    for line in lines[1:]:
        filetype, filepath, link, role, kind = line.split(",")
        _fake_files[filepath] = {
            "filetype": filetype,
            "filepath": filepath,
            "link": link,
            "role": role,
            "collection": (kind == "collection")
        }


def create_fake_files(fake_files):
    root = Path(current_app.config['FILE_ROOT_PATH'])
    for ff in fake_files.values():
        path = root / Path(ff['filepath'])
        path.parent.mkdir(exist_ok=True, parents=True)

        if ff['filetype'] == "f":
            path.touch(exist_ok=True)
        elif ff['filetype'] == "d":
            path.mkdir(exist_ok=True, parents=True)
        elif ff['filetype'] == "l" and not path.exists():
            link = root / Path(ff['link'])
            target_is_directory = True if fake_files[ff['link']]['filetype'] == "d" else False
            path.symlink_to(link, target_is_directory=target_is_directory)


@pytest.fixture
def fake_files():
    return _fake_files


@pytest.fixture
def app():
    root = "/tmp/pims-test"

    app = create_app({
        'TESTING': True,
        'FILE_ROOT_PATH': root,
    })

    with app.app_context():
        create_fake_files(_fake_files)

    yield app

    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@contextmanager
def not_raises(expected_exc):
    try:
        yield

    except expected_exc as err:
        raise AssertionError(
            "Did raise exception {0} when it should not!".format(
                repr(expected_exc)
            )
        )

    except Exception as err:
        raise AssertionError(
            "An unexpected exception {0} raised.".format(repr(err))
        )
