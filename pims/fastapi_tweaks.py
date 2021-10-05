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

import csv
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, List, Mapping, Sequence, Tuple, Union

from fastapi import params
from fastapi.dependencies import utils
from pydantic.error_wrappers import ErrorWrapper
from pydantic.errors import MissingError
from pydantic.fields import ModelField
from starlette.datastructures import Headers, QueryParams


# Fast API tweaks

# Waiting for PR2078 to be merged
# https://github.com/tiangolo/fastapi/pull/2078/
# Add support for query parameter serialization styles


class QueryStyle(Enum):
    form = "form"
    space_delimited = "spaceDelimited"
    pipe_delimited = "pipeDelimited"
    # deep_object = "deepObject"  # NOT SUPPORTED YET


query_style_to_delimiter = {
    QueryStyle.form: ",",
    QueryStyle.space_delimited: " ",
    QueryStyle.pipe_delimited: "|",
}

# Force our settings in the context of PIMS until PR is merged.
query_style = QueryStyle.form
query_explode = False


def request_params_to_args(
    required_params: Sequence[ModelField],
    received_params: Union[Mapping[str, Any], QueryParams, Headers],
) -> Tuple[Dict[str, Any], List[ErrorWrapper]]:
    values = {}
    errors = []
    for field in required_params:
        field_info = field.field_info
        assert isinstance(
            field_info, params.Param
        ), "Params must be subclasses of Param"

        if utils.is_scalar_sequence_field(field) and isinstance(
                received_params, (QueryParams, Headers)
        ):
            if isinstance(field_info, params.Query) and not query_explode:
                value = received_params.get(field.alias)
                if value is not None:
                    delimiter = query_style_to_delimiter.get(query_style)
                    value = list(csv.reader([value], delimiter=delimiter))[0]
            else:
                value = received_params.getlist(field.alias) or field.default
        else:
            value = received_params.get(field.alias)

        if value is None:
            if field.required:
                errors.append(
                    ErrorWrapper(
                        MissingError(), loc=(field_info.in_.value, field.alias)
                    )
                )
            else:
                values[field.name] = deepcopy(field.default)
            continue
        v_, errors_ = field.validate(
            value, values, loc=(field_info.in_.value, field.alias)
        )
        if isinstance(errors_, ErrorWrapper):
            errors.append(errors_)
        elif isinstance(errors_, list):
            errors.extend(errors_)
        else:
            values[field.name] = v_
    return values, errors


def apply_fastapi_tweaks():
    # Monkey patch Fast API
    utils.request_params_to_args = request_params_to_args
