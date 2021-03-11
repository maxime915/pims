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

from pims.api.exceptions import TooLargeOutputProblem
from pims.api.utils.image_parameter import get_rationed_resizing, get_output_dimensions, parse_planes, \
    check_reduction_validity, check_array_size, ensure_list, safeguard_output_dimensions, parse_intensity_bounds
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
    assert parse_planes([], 10, default=[1, 2]) == {1, 2}

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
    assert ensure_list(None) == []


def test_safeguard_output_dimensions():
    assert safeguard_output_dimensions('UNSAFE', 100, 10000, 10000) == (10000, 10000)
    assert safeguard_output_dimensions('SAFE_RESIZE', 100, 10, 99) == (10, 99)
    assert safeguard_output_dimensions('SAFE_RESIZE', 100, 1000, 2000) == (50, 100)
    assert safeguard_output_dimensions('SAFE_RESIZE', 100, 2000, 1000) == (100, 50)

    with pytest.raises(TooLargeOutputProblem):
        assert safeguard_output_dimensions('SAFE_REJECT', 100, 1000, 2000)

    with not_raises(TooLargeOutputProblem):
        assert safeguard_output_dimensions('SAFE_REJECT', 100, 10, 99)


def test_parse_intensity_bounds():
    class FakeImage:
        def __init__(self, significant_bits, n_channels):
            self.n_channels = n_channels
            self.significant_bits = significant_bits

        def channel_stats(self, channel):
            return dict(minimum=channel, maximum=channel + 10)

    assert parse_intensity_bounds(FakeImage(8, 1), [0], [], []) == ([0], [255])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], ["AUTO_IMAGE"], ["AUTO_IMAGE"]) == ([0], [255])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], ["STRETCH_IMAGE"], ["STRETCH_IMAGE"]) == ([0], [10])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], [10], [100]) == ([10], [100])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], [10], [1000]) == ([10], [255])

    assert parse_intensity_bounds(FakeImage(16, 1), [0], [], []) == ([0], [65535])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], ["AUTO_IMAGE"], ["AUTO_IMAGE"]) == ([0], [10])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], ["STRETCH_IMAGE"], ["STRETCH_IMAGE"]) == ([0], [10])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [10], [100]) == ([10], [100])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [10], [1000]) == ([10], [1000])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [10], [100000]) == ([10], [65535])

    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], ["AUTO_IMAGE"], ["AUTO_IMAGE"]) == ([0, 0], [255, 255])
    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], ["STRETCH_IMAGE"], ["STRETCH_IMAGE"]) == ([0, 1], [10, 11])
    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], [10], [100]) == ([10, 10], [100, 100])
    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], [10], [1000, 20]) == ([10, 10], [255, 20])

    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], ["AUTO_IMAGE"], ["AUTO_IMAGE"]) == ([0, 1], [10, 11])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], ["STRETCH_IMAGE"], ["STRETCH_IMAGE"]) == ([0, 1], [10, 11])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], [10], [100]) == ([10, 10], [100, 100])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], [10], [1000, 20]) == ([10, 10], [1000, 20])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1],  [10, 5], [100000, 20]) == ([10, 5], [65535, 20])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1],  [10, "AUTO_IMAGE"], [100000, 20]) == ([10, 1], [65535, 20])
