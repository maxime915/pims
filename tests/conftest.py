import os
import shutil
from pathlib import Path

import pytest
from flask import current_app

from pims.app import create_app

with open(os.path.join(os.path.dirname(__file__), 'fake_files.csv'), 'r') as f:
    _fake_files = f.read().splitlines()


def create_fake_files(fake_files):
    last_file = None
    for ff in fake_files:
        filetype, name, _ = ff.split(",")

        path = Path(current_app.config['FILE_ROOT_PATH'], name)
        path.parent.mkdir(exist_ok=True, parents=True)

        if filetype == "f":
            path.touch(exist_ok=True)
            last_file = path
        elif filetype == "l" and not path.exists():
            path.symlink_to(last_file)


@pytest.fixture
def fake_files():
    types, names, roles = list(), list(), list()
    for ff in _fake_files:
        filetype, name, role = ff.split(",")
        types.append(filetype)
        names.append(name)
        roles.append(role)
    return types, names, roles


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
