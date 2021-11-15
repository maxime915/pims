#  * Copyright (c) 2020-2021. Authors: see NOTICE file.
#  *
#  * Licensed under the Apache License, Version 2.0 (the "License");
#  * you may not use this file except in compliance with the License.
#  * You may obtain a copy of the License at
#  *
#  *      http://www.apache.org/licenses/LICENSE-2.0
#  *
#  * Unless required by applicable law or agreed to in writing, software
#  * distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.

from shapely.geometry import Point, box

from pims.api.utils.annotation_parameter import get_annotation_region, parse_annotation
from pims.processing.annotations import ParsedAnnotation, ParsedAnnotations
from pims.processing.region import Region
from pims.utils.color import Color


def test_parse_annotation():
    annot = {"geometry": "POINT (10 10)"}
    assert parse_annotation(**annot) == ParsedAnnotation(Point(10, 10))

    red = Color("red")
    white = Color("white")

    annot = {"geometry": "POINT (10 10)", "fill_color": white}
    default = {"fill_color": red, "stroke_color": white}

    assert parse_annotation(**annot, default=default) == ParsedAnnotation(
        Point(10, 10), white, white
    )
    assert parse_annotation(**annot) == ParsedAnnotation(Point(10, 10), white)
    assert parse_annotation(**annot, ignore_fields=['fill_color']) == ParsedAnnotation(
        Point(10, 10)
    )
    assert parse_annotation(
        **annot, ignore_fields=['fill_color'],
        default=default
    ) == ParsedAnnotation(Point(10, 10), stroke_color=white)


def test_annotation_region():
    class FakeImage:
        def __init__(self, w, h):
            self.width = w
            self.height = h

    al = ParsedAnnotations()
    al.append(ParsedAnnotation(box(10, 20, 30, 40)))
    assert get_annotation_region(FakeImage(100, 100), al) == Region(20, 10, 20, 20)
    assert get_annotation_region(FakeImage(100, 100), al, context_factor=1.5) == Region(
        15, 5, 30, 30
    )

    al = ParsedAnnotations()
    al.append(ParsedAnnotation(box(10, 20, 30, 30)))
    assert get_annotation_region(FakeImage(100, 100), al, try_square=True) == Region(
        15, 10, 20, 20
    )

    al = ParsedAnnotations()
    al.append(ParsedAnnotation(box(20, 10, 30, 30)))
    assert get_annotation_region(FakeImage(100, 100), al, try_square=True) == Region(
        10, 15, 20, 20
    )
