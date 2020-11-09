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


from enum import Enum
from io import BytesIO

from connexion import request, NoContent
from flask import send_file

from pims.api.exceptions import ColormapNotFoundProblem
from pims.api.utils.mimetype import mimetype_to_mpl_slug, JPEG_MIMETYPES, PNG_MIMETYPES
from pims.api.utils.response import response_list
from pims.processing.colormaps import COLORMAPS


class ColormapType(Enum):
    SEQUENTIAL = "SEQUENTIAL"
    DIVERGING = "DIVERGING"
    QUALITATIVE = "QUALITATIVE"


def _serialize_colormap(colormap, colormap_id):
    return {
        'id': colormap_id,
        'n_colors': colormap.number,
        'name': colormap.name,
        'type': ColormapType[colormap.type.upper()].value
    }


def list_colormaps():
    colormaps = [_serialize_colormap(c, cid) for cid, c in COLORMAPS.items()]
    return response_list(colormaps)


def show_colormap(colormap_id):
    if colormap_id not in COLORMAPS.keys():
        raise ColormapNotFoundProblem(colormap_id)

    return _serialize_colormap(COLORMAPS[colormap_id], colormap_id)


def show_colormap_representation(colormap_id, width, height):
    # TODO: handle request and response headers

    if colormap_id not in COLORMAPS.keys():
        raise ColormapNotFoundProblem(colormap_id)

    SUPPORTED_MIMETYPES = dict()
    SUPPORTED_MIMETYPES.update(PNG_MIMETYPES)
    SUPPORTED_MIMETYPES.update(JPEG_MIMETYPES)
    response_mimetype = request.accept_mimetypes.best_match(SUPPORTED_MIMETYPES.keys())
    if response_mimetype is None:
        return NoContent, 406

    fp = BytesIO()

    # Palette._write_image uses Matplotlib size in inches.
    width = round(width / 100, 2)
    height = round(height / 100, 2)

    format_slug = mimetype_to_mpl_slug(response_mimetype)
    colormap = COLORMAPS[colormap_id]
    colormap._write_image(fp, 'discrete', format=format_slug, size=(width, height))

    fp.seek(0)
    return send_file(fp, mimetype=response_mimetype)
