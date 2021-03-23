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
from shapely.wkt import loads as wkt_loads
from shapely.validation import explain_validity, make_valid

from pims.api.utils.schema_format import parse_color
from pims.processing.annotations import Annotation, AnnotationList
from pims.processing.region import Region


def parse_annotations(annotations, ignore_fields=None, default=None,
                      point_envelope_length=None):
    """
    Parse a list of annotations.

    Parameters
    ----------
    annotations : list of dict
        List of annotations, as defined in API spec.
    ignore_fields : list of str or None
        List of field names to ignore for parsing.
    default : dict (optional)
        Default value for fields. Default value for missing fields is None.
    point_envelope_length : int (optional)
        Envelope length for Point geometries.

    Returns
    -------
    AnnotationList
        A list of parsed annotations
    """

    al = AnnotationList()
    for annotation in annotations:
        al.append(parse_annotation(**annotation, ignore_fields=ignore_fields,
                                   default=default, point_envelope_length=point_envelope_length))

    return al


def parse_annotation(geometry, fill_color=None, stroke_color=None,
                     stroke_width=None, ignore_fields=None, default=None,
                     point_envelope_length=None):
    """
    Parse an annotation.

    Parameters
    ----------
    geometry : str
        valid WKT string to parse (parsed geometry can be invalid)
    fill_color : str (optional)
        Fill color to parse
    stroke_color : str (optional)
        Stroke color to parse
    stroke_width : int (optional)
        Stroke width to parse
    ignore_fields : list of str (optional)
        List of field names to ignore for parsing.
    default : dict (optional)
        Default value for fields. Default value for missing fields is None.
    point_envelope_length : int (optional)
        Envelope length for Point geometries.

    Returns
    -------
    Annotation
        A parsed annotation

    Raises
    ------
    BadRequestProblem
        If geometry is invalid, even after trying to make it valid.
    """
    if ignore_fields is None:
        ignore_fields = []

    if default is None:
        default = dict()

    geom = wkt_loads(geometry)
    if not geom.is_valid:
        geom = make_valid(geom)

    if not geom.is_valid:
        raise BadRequestProblem(detail="{} is invalid. Reason: {}".format(
            geometry, explain_validity(geom)))
    parsed = {'geometry': geom}

    if geom.type == 'Point' and point_envelope_length is not None:
        parsed['point_envelope_length'] = point_envelope_length

    if 'fill_color' not in ignore_fields:
        default_color = default.get('fill_color')
        default_color = parse_color(default_color) if default_color else default_color
        parsed['fill_color'] = parse_color(fill_color) \
            if fill_color is not None else default_color

    if 'stroke_color' not in ignore_fields:
        default_color = default.get('stroke_color')
        default_color = parse_color(default_color) if default_color else default_color
        parsed['stroke_color'] = parse_color(stroke_color) \
            if stroke_color is not None else default_color

    if 'stroke_width' not in ignore_fields:
        parsed['stroke_width'] = stroke_width \
            if stroke_width is not None else default.get('stroke_width')

    return Annotation(**parsed)


def get_annotation_region(in_image, annots, context_factor=1.0, try_square=False):
    """
    Get the region describing the rectangular envelope of all
    annotations multiplied by an optional context factor.

    Parameters
    ----------
    in_image : Image
        Image in which region is extracted.
    annots : AnnotationList
        List of parsed annotations
    context_factor : float
        Context factor
    try_square : bool
        Try to adapt region's width or height to have a square region.
    Returns
    -------
    Region
    """

    # All computation are done in non normalized float.
    minx, miny, maxx, maxy = annots.bounds
    left = minx
    top = miny
    width = maxx - minx
    height = maxy - miny
    if context_factor and context_factor != 1.0:
        left -= width * (context_factor - 1) / 2.0
        top -= height * (context_factor - 1) / 2.0
        width *= context_factor
        height *= context_factor

    if try_square:
        if width < height:
            delta = height - width
            left -= delta / 2
            width += delta
        elif height < width:
            delta = width - height
            top -= delta / 2
            height += delta

    width = min(width, in_image.width)
    if left < 0:
        left = 0
    else:
        left = min(left, in_image.width - width)

    height = min(height, in_image.height)
    if top < 0:
        top = 0
    else:
        top = min(top, in_image.height - height)

    return Region(top, left, width, height)
