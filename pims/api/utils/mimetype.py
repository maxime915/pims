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
from collections import OrderedDict

from pims import PIMS_SLUG_PNG, PIMS_SLUG_WEBP, PIMS_SLUG_JPEG
from pims.api.exceptions import NoAcceptableResponseMimetypeProblem

PNG_MIMETYPES = {
    "image/png": PIMS_SLUG_PNG,
    "image/apng":  PIMS_SLUG_PNG
}
WEBP_MIMETYPES = {
    "image/webp": PIMS_SLUG_WEBP
}
JPEG_MIMETYPES = {
    "image/jpg": PIMS_SLUG_JPEG,
    "image/jpeg": PIMS_SLUG_JPEG
}


def build_mimetype_dict(*mimetype_dicts):
    """Build an ordered dict from a list of dicts.
    Order in these sub-dictionaries is not guaranteed.
    """
    ordered_mimetypes = OrderedDict()
    for mimetype_dict in mimetype_dicts:
        ordered_mimetypes.update(mimetype_dict)
    return ordered_mimetypes


VISUALISATION_MIMETYPES = build_mimetype_dict(WEBP_MIMETYPES, JPEG_MIMETYPES, PNG_MIMETYPES)
PROCESSING_MIMETYPES = build_mimetype_dict(PNG_MIMETYPES, JPEG_MIMETYPES, WEBP_MIMETYPES)


def get_output_format(request, supported):
    """
    Get the best output/response format and mime type according to
    the request and the ordered dictionary of supported mime types.

    Parameters
    ----------
    request : request
    supported : OrderedDict
        Ordered dictionary of supported mime types.

    Returns
    -------
    output_format : str
        PIMS slug for the best match
    output_mimetype : str
        Mime type associated to the output format

    Raises
    ------
    NoAcceptableResponseMimetypeProblem
        If there is no acceptable mime type.
    """
    response_mimetype = request.accept_mimetypes.best_match(supported.keys())
    output_format = supported.get(response_mimetype)
    if output_format:
        return output_format, response_mimetype

    raise NoAcceptableResponseMimetypeProblem(str(request.accept_mimetypes), list(supported.keys()))
