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

from pims.api.utils.image_parameter import get_rationed_resizing, get_output_dimensions


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
