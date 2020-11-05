from enum import Enum
from io import BytesIO

from connexion import request, NoContent
from flask import send_file

from pims.api.exceptions import ColormapNotFoundProblem
from pims.api.utils import mimetype_to_mpl_slug, JPEG_MIMETYPES, PNG_MIMETYPES
from pims.processing.colormaps import COLORMAPS


class ColormapType(Enum):
    SEQUENTIAL = "SEQUENTIAL"
    DIVERGING = "DIVERGING"
    QUALITATIVE = "QUALITATIVE"


def _colormap_to_dict(colormap, colormap_id):
    return {
        'id': colormap_id,
        'n_colors': colormap.number,
        'name': colormap.name,
        'type': ColormapType[colormap.type.upper()].value
    }


def list():
    colormaps = [_colormap_to_dict(c, cid) for cid, c in COLORMAPS.items()]
    return {
        "items": colormaps,
        "size": len(colormaps)
    }


def show(colormap_id):
    if colormap_id not in COLORMAPS.keys():
        raise ColormapNotFoundProblem(colormap_id)

    return _colormap_to_dict(COLORMAPS[colormap_id], colormap_id)


def representation(colormap_id, width, height):
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
