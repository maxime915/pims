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
from typing import List, Optional

from pydantic import BaseModel, Field

from pims.api.exceptions import FormatNotFoundProblem
from pims.api.utils.models import CollectionSize, FormatId
from pims.api.utils.response import response_list
from pims.formats import FORMATS

from fastapi import APIRouter

router = APIRouter()
api_tags = ['Formats']


class Format(BaseModel):
    id: FormatId
    name: str = Field(
        ..., description='Readable format name', example='Hamamatsu VMS'
    )
    remarks: Optional[str] = Field(
        None, description='Readable end-user remarks about the format',
    )
    convertible: bool = Field(
        ..., description='Whether the format can be converted into another one or not.'
    )
    readable: bool = Field(
        ...,
        description='Whether the format is natively readable by PIMS or not. '
                    'Non readable formats should be convertible.',
    )
    writable: bool = Field(
        False, description='Whether PIMS can write a file in this format or not.'
    )
    plugin: Optional[str] = Field(
        None,
        description='PIMS plugin providing this format, returned as a Python module.',
        example='pims.formats.common',
    )


class FormatsList(CollectionSize):
    items: List[Format] = Field(None, description='Array of formats', title='Format')


def _serialize_format(format):
    return Format(
        id=format.get_identifier(),
        name=format.get_name(),
        remarks=format.get_remarks(),
        readable=format.is_readable(),
        writable=format.is_writable(),
        convertible=format.is_convertible(),
        plugin=format.get_plugin_name()
    )


@router.get('/formats', response_model=FormatsList, tags=api_tags)
def list_formats():
    """
    List all formats
    """
    formats = [_serialize_format(format) for format in FORMATS.values()]
    return response_list(formats)


@router.get('/formats/{format_id}', response_model=Format, tags=api_tags)
def show_format(format_id: str):
    """
    Get a format
    """
    format_id = format_id.upper()
    if format_id not in FORMATS.keys():
        raise FormatNotFoundProblem(format_id)
    return _serialize_format(FORMATS[format_id])
