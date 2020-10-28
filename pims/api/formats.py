from connexion import ProblemException

from pims.formats import FORMATS


class FormatNotFoundProblem(ProblemException):
    def __init__(self, colormap_id):
        title = 'Format not found'
        detail = 'The format {} does not exist.'.format(colormap_id)
        type = "problem/resource-not-found"
        super(FormatNotFoundProblem, self).__init__(status=404, title=title, detail=detail, type=type)


def _format_to_dict(format):
    return {
        "id": format.get_identifier(),
        "name": format.get_name(),
        "remarks": format.get_remarks(),
        "readable": format.is_readable(),
        "writable": format.is_writable(),
        "convertible": format.is_convertible(),
        "plugin": format.get_plugin_name()
    }


def list():
    formats = [_format_to_dict(format) for format in FORMATS.values()]
    return {
        "items": formats,
        "size": len(formats)
    }


def show(format_id):
    format_id = format_id.upper()
    if format_id not in FORMATS.keys():
        raise FormatNotFoundProblem(format_id)
    return _format_to_dict(FORMATS[format_id])

