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
from connexion.exceptions import BadRequestProblem

from pims.api.utils.image_parameter import get_rationed_resizing, get_output_dimensions, parse_planes, \
    check_reduction_validity, check_array_size, ensure_list
from tests.conftest import not_raises


def test_get_rationed_resizing():
    assert get_rationed_resizing(50, 100, 200) == (50, 100)
    assert get_rationed_resizing(0.5, 100, 200) == (50, 100)


def test_get_output_dimensions():
    class FakeImage:
        def __init__(self, width, height):
            self.width = width
            self.height = height

    assert get_output_dimensions(FakeImage(1000, 2000), height=200) == (100, 200)
    assert get_output_dimensions(FakeImage(1000, 2000), width=100) == (100, 200)
    assert get_output_dimensions(FakeImage(1000, 2000), length=200) == (100, 200)
    assert get_output_dimensions(FakeImage(2000, 1000), length=200) == (200, 100)
    assert get_output_dimensions(FakeImage(1000, 2000), width=20, length=3, height=500) == (250, 500)

    with pytest.raises(BadRequestProblem):
        get_output_dimensions(FakeImage(1000, 2000))


def test_parse_planes():
    assert parse_planes([], 10) == {0}
    assert parse_planes([1, 2], 10) == {1, 2}
    assert parse_planes([1, 2, 200], 10) == {1, 2}
    assert parse_planes([2, '5:'], 8) == {2, 5, 6, 7}
    assert parse_planes([':'], 3) == {0, 1, 2}
    assert parse_planes(None, 10, default=[1, 2]) == {1, 2}

    with pytest.raises(BadRequestProblem):
        parse_planes([2, '5:', 'foo'], 10)


def test_check_reduction_validity():
    with not_raises(BadRequestProblem):
        check_reduction_validity([0], None)
        check_reduction_validity([], None)
        check_reduction_validity([1, 2], "SUM")

    with pytest.raises(BadRequestProblem):
        check_reduction_validity([1, 2], None)


def test_check_array_size():
    with not_raises(BadRequestProblem):
        check_array_size([1], [1, 2], True)
        check_array_size(None, [1, 2], True)

    with pytest.raises(BadRequestProblem):
        check_array_size([1], [2], True)
        check_array_size(None, [1], False)
        check_array_size([1], [], True)


def test_ensure_list():
    assert ensure_list(3) == [3]
    assert ensure_list((2, 4)) == [(2, 4)]
    assert ensure_list("a") == ['a']
    assert ensure_list([2]) == [2]
    assert ensure_list(None) is None
