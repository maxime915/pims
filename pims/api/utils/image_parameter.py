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
from connexion.exceptions import BadRequestProblem

from pims.api.utils.schema_format import parse_range, is_range


def get_shape_with_ratio(length1, image_length1, image_length2):
    factor = length1 if type(length1) == float else length1 / image_length1
    length1 = length1 if type(length1) == int else round(factor * image_length1)
    length2 = round(factor * image_length2)
    return length1, length2


def get_output_dimensions(in_image, height, width, length):
    if height is not None:
        out_height, out_width = get_shape_with_ratio(height, in_image.height, in_image.width)
    elif width is not None:
        out_width, out_height = get_shape_with_ratio(width, in_image.width, in_image.height)
    elif length is not None:
        if in_image.width > in_image.height:
            out_width, out_height = get_shape_with_ratio(length, in_image.width, in_image.height)
        else:
            out_height, out_width = get_shape_with_ratio(height, in_image.height, in_image.width)
    else:
        raise BadRequestProblem(detail='Impossible to determine output dimensions')

    return out_width, out_height


def get_parsed_planes(planes, reduction, n_planes):
    plane_indexes = list()
    for plane in planes:
        if type(plane) == int:
            plane_indexes.append(plane)
        elif is_range(plane):
            plane_indexes += [*parse_range(plane, 0, n_planes)]
        else:
            raise BadRequestProblem("Invalid plane index/range")

    plane_indexes = set([idx for idx in plane_indexes if 0 <= idx < n_planes])
    if len(plane_indexes) > 1 and reduction is None:
        raise BadRequestProblem("Missing reduction")

    return plane_indexes, reduction


def get_channel_planes(image, planes, reduction):
    """
    Image channels used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, all channels are considered.
    """
    if not planes:
        plane_indexes = [*range(0, image.n_channels)]
        return plane_indexes, reduction
    return get_parsed_planes(planes, reduction, image.n_channels)


def get_z_slice_planes(image, planes, reduction):
    """
    Image focal planes used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, the median focal plane is considered.
    """
    if not planes:
        return round(image.depth / 2), reduction
    return get_parsed_planes(planes, reduction, image.depth)


def get_timepoint_planes(image, planes, reduction):
    """
    Image timepoints used to render the response.
    This parameter is interpreted as a set such that duplicates are ignored.
    By default, the first timepoint considered.
    """
    if not planes:
        return 0, reduction
    return get_parsed_planes(planes, reduction, image.duration)


def check_array_size(array, allowed, nullable=True):
    if array is None:
        if not nullable:
            raise BadRequestProblem()
        return

    if not len(array) in allowed:
        raise BadRequestProblem("Bad array size")


def ensure_list(value):
    if value is not None:
        return value if type(value) == list else [value]
    return value
