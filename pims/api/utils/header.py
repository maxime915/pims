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


def serialize_header(value, style='simple', explode=False):
    """
    Serialize a header according to https://swagger.io/docs/specification/serialization/.

    Parameters
    ----------
    value :
        Value to serialize
    style : str ('simple')
        Serialization style.
    explode : bool
        Explode the object serialization.

    Returns
    -------
    str
        Serialized header.
    """
    if type(value) is list:
        return ','.join([str(item) for item in value])
    elif type(value) is dict:
        sep = '=' if explode else ','
        return ','.join(['{}{}{}'.format(k, sep, v) for k, v in value.items()])
    else:
        return str(value)


def add_image_size_limit_header(headers, request_width, request_height, safe_width, safe_height):
    """
    Add X-Image-Size-Limit header to existing header dict if necessary.

    Parameters
    ----------
    headers : dict
        Dict of headers to modify in place
    request_width : int
        Width requested by the user
    request_height : int
        Height requested by the user
    safe_width : int
        Safe width for this request
    safe_height : int
        Safe height for this request

    Returns
    -------
    headers : dict
        The header dict possibly updated with X-Image-Size-Limit
    """
    ratio = safe_width / request_width
    if ratio != 1.0:
        header = {
            'request_width': request_width,
            'request_height': request_height,
            'safe_width': safe_width,
            'safe_height': safe_height,
            'ratio': ratio
        }
        headers['X-Image-Size-Limit'] = serialize_header(header, explode=True)

    return headers
