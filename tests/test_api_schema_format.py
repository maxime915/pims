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

from pims.api.utils.schema_format import is_range, parse_range, is_color, parse_color


def test_is_range():
    assert is_range("10:20") is True
    assert is_range("20:10") is True
    assert is_range(":10") is True
    assert is_range("10:") is True
    assert is_range(":") is True
    assert is_range("a") is False
    assert is_range("2:3:4") is False


def test_parse_range():
    assert parse_range("10:20", 0, 100) == range(10, 20)
    assert parse_range("20:10", 0, 100) == range(10, 20)
    assert parse_range(":10", 0, 100) == range(0, 10)
    assert parse_range("10:", 0, 100) == range(10, 100)
    assert parse_range(":", 0, 100) == range(0, 100)

    with pytest.raises(ValueError):
        parse_range("a", 0, 100)

    with pytest.raises(ValueError):
        parse_range("2:3:4", 0, 100)


def test_is_color():
    assert is_color("red") is True
    assert is_color("foo") is False
    assert is_color("#fff") is True
    assert is_color("#ffffff") is True
    assert is_color("#ff") is False
    assert is_color("#ggg") is False
    assert is_color("rgb(10, 20, 30)") is True
    assert is_color("rgb (10, 20, 30)") is False
    assert is_color("rgb(10,20,c)") is False
    assert is_color("rgb(10%, 5.3%, 2)") is True


def test_parse_color():
    assert parse_color("red") == (255, 0, 0)
    assert parse_color("#fff") == (255, 255, 255)
    assert parse_color("#ffffff") == (255, 255, 255)
    assert parse_color("rgb(10, 20, 30)") == (10, 20, 30)
    assert parse_color("RGB(10, 20, 30)") == (10, 20, 30)
    assert parse_color("rgb(10%, 5.3%, 2)") == (26, 14, 5)

    with pytest.raises(ValueError):
        parse_color("#ggg")

    with pytest.raises(ValueError):
        parse_color("foo")

    with pytest.raises(ValueError):
        parse_color("rgb (10, 20, 30)")
