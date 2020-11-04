import os
import shutil
from pathlib import Path

import pytest
from flask import current_app

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
