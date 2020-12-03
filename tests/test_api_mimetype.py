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
import pytest
from flask import request

from pims.api.exceptions import NoAcceptableResponseMimetypeProblem
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES, PROCESSING_MIMETYPES


def test_get_output_format_simple(app):
    with app.test_request_context('/', headers={'Accept': 'image/jpg'}):
        format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
        assert format == "JPEG"
        assert mimetype == "image/jpg"


def test_get_output_format_complex(app):
    accept_header = 'application/signed-exchange;v=b3;q=0.9,text/html,application/xhtml+xml,image/webp,image/apng,' \
        'application/xml;q=0.9,*/*;q=0.8'
    with app.test_request_context('/', headers={'Accept': accept_header}):
        format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
        assert format == "WEBP"
        assert mimetype == "image/webp"

        format, mimetype = get_output_format(request, PROCESSING_MIMETYPES)
        assert format == "PNG"
        assert mimetype == "image/apng"


def test_get_output_format_accept_all(app):
    with app.test_request_context('/', headers={'Accept': 'image/*'}):
        format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
        assert format == "WEBP"
        assert mimetype == "image/webp"


def test_get_output_format_invalid(app):
    accept_header = 'application/json'
    with app.test_request_context('/', headers={'Accept': accept_header}):
        with pytest.raises(NoAcceptableResponseMimetypeProblem):
            get_output_format(request, VISUALISATION_MIMETYPES)
