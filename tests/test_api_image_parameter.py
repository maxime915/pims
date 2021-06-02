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
from pims.api.utils.header import SafeMode
from pims.api.utils.image_parameter import get_rationed_resizing, get_thumb_output_dimensions, parse_planes, \
    check_reduction_validity, check_array_size, ensure_list, safeguard_output_dimensions, parse_intensity_bounds, \
    check_level_validity, check_zoom_validity, check_tileindex_validity, check_tilecoord_validity, parse_region
from pims.api.utils.models import IntensitySelectionEnum, TierIndexType
from pims.formats.utils.pyramid import Pyramid
from pims.processing.region import Region
from tests.conftest import not_raises


def test_get_rationed_resizing():
    assert get_rationed_resizing(50, 100, 200) == (50, 100)
    assert get_rationed_resizing(0.5, 100, 200) == (50, 100)


def test_get_output_dimensions():
    class FakeImage:
        def __init__(self, width, height):
            self.width = width
            self.height = height

    assert get_thumb_output_dimensions(FakeImage(1000, 2000), height=200) == (100, 200)
    assert get_thumb_output_dimensions(FakeImage(1000, 2000), width=100) == (100, 200)
    assert get_thumb_output_dimensions(FakeImage(1000, 2000), length=200) == (100, 200)
    assert get_thumb_output_dimensions(FakeImage(2000, 1000), length=200) == (200, 100)
    assert get_thumb_output_dimensions(FakeImage(1000, 2000), width=20, length=3, height=500) == (250, 500)

    with pytest.raises(BadRequestProblem):
        get_thumb_output_dimensions(FakeImage(1000, 2000))


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
    assert safeguard_output_dimensions(SafeMode.UNSAFE, 100, 10000, 10000) == (10000, 10000)
    assert safeguard_output_dimensions(SafeMode.RESIZE, 100, 10, 99) == (10, 99)
    assert safeguard_output_dimensions(SafeMode.RESIZE, 100, 1000, 2000) == (50, 100)
    assert safeguard_output_dimensions(SafeMode.RESIZE, 100, 2000, 1000) == (100, 50)

    with pytest.raises(TooLargeOutputProblem):
        assert safeguard_output_dimensions(SafeMode.REJECT, 100, 1000, 2000)

    with not_raises(TooLargeOutputProblem):
        assert safeguard_output_dimensions(SafeMode.REJECT, 100, 10, 99)


def test_parse_intensity_bounds():
    class FakeImage:
        def __init__(self, significant_bits, n_channels):
            self.n_channels = n_channels
            self.significant_bits = significant_bits

        def channel_stats(self, channel):
            return dict(minimum=channel, maximum=channel + 10)

    assert parse_intensity_bounds(FakeImage(8, 1), [0], [], []) == ([0], [255])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0], [255])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0], [10])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], [10], [100]) == ([10], [100])
    assert parse_intensity_bounds(FakeImage(8, 1), [0], [10], [1000]) == ([10], [255])

    assert parse_intensity_bounds(FakeImage(16, 1), [0], [], []) == ([0], [65535])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0], [10])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0], [10])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [10], [100]) == ([10], [100])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [10], [1000]) == ([10], [1000])
    assert parse_intensity_bounds(FakeImage(16, 1), [0], [10], [100000]) == ([10], [65535])

    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0, 0], [255, 255])
    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0, 1], [10, 11])
    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], [10], [100]) == ([10, 10], [100, 100])
    assert parse_intensity_bounds(FakeImage(8, 2), [0, 1], [10], [1000, 20]) == ([10, 10], [255, 20])

    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0, 1], [10, 11])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], [IntensitySelectionEnum.AUTO_IMAGE], [IntensitySelectionEnum.AUTO_IMAGE]) == ([0, 1], [10, 11])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], [10], [100]) == ([10, 10], [100, 100])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1], [10], [1000, 20]) == ([10, 10], [1000, 20])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1],  [10, 5], [100000, 20]) == ([10, 5], [65535, 20])
    assert parse_intensity_bounds(FakeImage(16, 2), [0, 1],  [10, IntensitySelectionEnum.AUTO_IMAGE], [100000, 20]) == ([10, 1], [65535, 20])


class FakeImagePyramid:
    def __init__(self, width, height, n_tiers):
        self.pyramid = Pyramid()
        for i in range(n_tiers):
            self.pyramid.insert_tier(width / (2**i), height / (2**i), 256)


def test_check_level_validity():
    with not_raises(BadRequestProblem):
        check_level_validity(FakeImagePyramid(100, 100, 1).pyramid, 0)
        check_level_validity(FakeImagePyramid(100, 100, 20).pyramid, 10)
        check_level_validity(FakeImagePyramid(100, 100, 20).pyramid, None)

    with pytest.raises(BadRequestProblem):
        check_level_validity(FakeImagePyramid(100, 100, 1).pyramid, 1)

    with pytest.raises(BadRequestProblem):
        check_level_validity(FakeImagePyramid(100, 100, 20).pyramid, 25)


def test_check_zoom_validity():
    with not_raises(BadRequestProblem):
        check_zoom_validity(FakeImagePyramid(100, 100, 1).pyramid, 0)
        check_zoom_validity(FakeImagePyramid(100, 100, 20).pyramid, 10)
        check_zoom_validity(FakeImagePyramid(100, 100, 20).pyramid, None)

    with pytest.raises(BadRequestProblem):
        check_zoom_validity(FakeImagePyramid(100, 100, 1).pyramid, 1)

    with pytest.raises(BadRequestProblem):
        check_zoom_validity(FakeImagePyramid(100, 100, 20).pyramid, 25)


def test_check_tileindex_validity():
    img = FakeImagePyramid(1000, 2000, 1)

    with not_raises(BadRequestProblem):
        check_tileindex_validity(img.pyramid, 0, 0, TierIndexType.ZOOM)
        check_tileindex_validity(img.pyramid, 0, 0, TierIndexType.LEVEL)
        check_tileindex_validity(img.pyramid, 31, 0, TierIndexType.ZOOM)
        check_tileindex_validity(img.pyramid, 31, 0, TierIndexType.LEVEL)

    with pytest.raises(BadRequestProblem):
        check_tileindex_validity(img.pyramid, 32, 0, TierIndexType.ZOOM)

    with pytest.raises(BadRequestProblem):
        check_tileindex_validity(img.pyramid, -1, 0, TierIndexType.ZOOM)


def test_check_tilecoord_validity():
    img = FakeImagePyramid(1000, 2000, 1)

    with not_raises(BadRequestProblem):
        check_tilecoord_validity(img.pyramid, 0, 0, 0, TierIndexType.ZOOM)
        check_tilecoord_validity(img.pyramid, 0, 0, 0, TierIndexType.LEVEL)
        check_tilecoord_validity(img.pyramid, 3, 7, 0, TierIndexType.ZOOM)
        check_tilecoord_validity(img.pyramid, 3, 7, 0, TierIndexType.LEVEL)

    with pytest.raises(BadRequestProblem):
        check_tilecoord_validity(img.pyramid, 3, 8, 0, TierIndexType.ZOOM)

    with pytest.raises(BadRequestProblem):
        check_tilecoord_validity(img.pyramid, -1, 0, 0, TierIndexType.ZOOM)


def test_parse_region():
    img = FakeImagePyramid(1000, 2000, 3)

    region = {'top': 100, 'left': 50, 'width': 128, 'height': 128}
    assert parse_region(img, region, 0, TierIndexType.LEVEL) == Region(100, 50, 128, 128)
    assert parse_region(img, region, 1, TierIndexType.LEVEL) == Region(100, 50, 128, 128, downsample=2)

    region = {'top': 0.1, 'left': 0.15, 'width': 0.02, 'height': 0.2}
    assert parse_region(img, region, 0, TierIndexType.LEVEL) == Region(200, 150, 20, 400)
    assert parse_region(img, region, 1, TierIndexType.LEVEL) == Region(100, 75, 10, 200, downsample=2)

    with pytest.raises(BadRequestProblem):
        region = {'top': 100, 'left': 900, 'width': 128, 'height': 128}
        parse_region(img, region, 0, TierIndexType.LEVEL)
