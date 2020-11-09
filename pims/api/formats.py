from pims.api.exceptions import FormatNotFoundProblem
from pims.formats import FORMATS


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


def list_formats():
    formats = [_format_to_dict(format) for format in FORMATS.values()]
    return {
        "items": formats,
        "size": len(formats)
    }


def show_format(format_id):
    format_id = format_id.upper()
    if format_id not in FORMATS.keys():
        raise FormatNotFoundProblem(format_id)
    return _format_to_dict(FORMATS[format_id])
