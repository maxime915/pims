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
from pims.connexion_utils import coerce_type


def test_coerce_type_simple():
    schema = {'x-scope': [''], 'name': 'filepath', 'in': 'path', 'description': 'The file path, relative to server base path.', 'required': True, 'schema': {'type': 'string', 'format': 'path'}, 'example': '123/my-file.ext'}
    value = 'abc/def'
    assert coerce_type(schema, value) == value

def test_coerce_type_length():
    schema = {'x-scope': [''], 'name': 'length', 'in': 'query', 'description': 'Length of the largest side of the thumbnail. The other dimension is adjusted to preserve the aspect ratio.\n\n**Ignored if other size-related parameter such as `width` or `height` is present.**\n', 'required': False, 'schema': {'x-scope': ['', '#/components/parameters/query-thumb-length'], 'x-default': 256, 'allOf': [{'default': 256}, {'x-scope': ['', '#/components/parameters/query-thumb-length', '#/components/schemas/target-length-default-256'], 'description': 'Length of the largest side of the target. The other dimension is adjusted to preserve the aspect\nratio.\n', 'example': 256, 'oneOf': [{'type': 'integer', 'format': 'int64', 'description': 'A length in pixels.', 'minimum': 0, 'example': 256}, {'type': 'number', 'format': 'double', 'description': 'A length expressed in percentage relatively to the real image length.', 'minimum': 0.0, 'maximum': 1.0, 'example': 0.5}]}]}}
    assert coerce_type(schema, '100') == 100
    assert coerce_type(schema, '1.1') == 1.1

def test_coerce_type_channels():
    schema = {'x-scope': [''], 'name': 'channels', 'in': 'query', 'required': False, 'style': 'form', 'explode': False, 'schema': {'x-scope': ['', '#/components/parameters/query-channel-selection'], 'x-single-or-array': True, 'description': 'Image channels used to render the response.\nThis parameter is interpreted as a set such that duplicates are ignored.\n**By default**, all channels are considered.\n\nThe reduction operation to merge the channels can be set in `c_reduction` parameter.\n', 'oneOf': [{'x-scope': ['', '#/components/parameters/query-channel-selection', '#/components/schemas/multiple-channel-indexes'], 'type': 'integer', 'format': 'int32', 'description': 'A single channel index', 'minimum': 0}, {'x-scope': ['', '#/components/parameters/query-channel-selection', '#/components/schemas/multiple-channel-indexes'], 'type': 'string', 'format': 'range', 'description': 'A range of channel indexes. Start index is inclusive, last one exclusive and must be separated by `:`.', 'example': '2:6'}, {'type': 'array', 'items': {'oneOf': [{'x-scope': ['', '#/components/parameters/query-channel-selection', '#/components/schemas/multiple-channel-indexes'], 'type': 'integer', 'format': 'int32', 'description': 'A single channel index', 'minimum': 0}, {'x-scope': ['', '#/components/parameters/query-channel-selection', '#/components/schemas/multiple-channel-indexes'], 'type': 'string', 'format': 'range', 'description': 'A range of channel indexes. Start index is inclusive, last one exclusive and must be separated by `:`.', 'example': '2:6'}]}}]}}
    assert coerce_type(schema, '2') == 2
    assert coerce_type(schema, ['2:4', '5']) == ['2:4', 5]

def test_coerce_type_gammas():
    schema = {'x-scope': [''], 'name': 'gammas', 'in': 'query', 'required': False, 'style': 'form', 'explode': False, 'schema': {'x-scope': ['', '#/components/parameters/query-gammas'], 'description': 'Gamma performs a non-linear histogram adjustment. Pixel intensities in the original image are raised\nto the power of the gamma value.\n\nIf `gamma < 1`, faint objects become more intense while bright objects do not.\n\nIf `gamma > 1`, medium-intensity objects become fainter while bright objects do not.\n', 'x-default': 1, 'x-single-or-array': True, 'oneOf': [{'allOf': [{'default': 1}, {'x-scope': ['', '#/components/parameters/query-gammas', '#/components/schemas/gamma-list'], 'type': 'number', 'format': 'double', 'minimum': 0, 'maximum': 10}]}, {'type': 'array', 'description': 'Expected format is an array of size:\n* 1 to apply the gamma correction to all channels\n* equals to the number of channels used to render the response in order to apply the gamma correction\nper channel.\n', 'minItems': 1, 'items': {'x-scope': ['', '#/components/parameters/query-gammas', '#/components/schemas/gamma-list'], 'type': 'number', 'format': 'double', 'minimum': 0, 'maximum': 10}}]}}
    assert coerce_type(schema, '1') == 1
    assert coerce_type(schema, ['1', '2']) == [1, 2]