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
import asyncio
import csv
import email
import json
from copy import deepcopy
from enum import Enum
from typing import (
    Any, Callable, Coroutine, Dict, List, Mapping, Optional, Sequence, Tuple, Type,
    Union
)

from fastapi import params, routing
from fastapi.datastructures import Default, DefaultPlaceholder
from fastapi.dependencies import utils
from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import solve_dependencies
from fastapi.encoders import DictIntStrAny, SetIntStr
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.routing import run_endpoint_function, serialize_response
from pydantic.error_wrappers import ErrorWrapper
from pydantic.errors import MissingError
from pydantic.fields import ModelField, Undefined
from starlette.datastructures import Headers, QueryParams
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from pims.api.utils.response import FastJsonResponse


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


######


# fastapi/routing.py#164
# Tweak so that FastJsonResponse bypasses response validation & jsonable_encoder


def get_request_handler(
    dependant: Dependant,
    body_field: Optional[ModelField] = None,
    status_code: Optional[int] = None,
    response_class: Union[Type[Response], DefaultPlaceholder] = Default(JSONResponse),
    response_field: Optional[ModelField] = None,
    response_model_include: Optional[Union[SetIntStr, DictIntStrAny]] = None,
    response_model_exclude: Optional[Union[SetIntStr, DictIntStrAny]] = None,
    response_model_by_alias: bool = True,
    response_model_exclude_unset: bool = False,
    response_model_exclude_defaults: bool = False,
    response_model_exclude_none: bool = False,
    dependency_overrides_provider: Optional[Any] = None,
) -> Callable[[Request], Coroutine[Any, Any, Response]]:
    assert dependant.call is not None, "dependant.call must be a function"
    is_coroutine = asyncio.iscoroutinefunction(dependant.call)
    is_body_form = body_field and isinstance(body_field.field_info, params.Form)
    if isinstance(response_class, DefaultPlaceholder):
        actual_response_class: Type[Response] = response_class.value
    else:
        actual_response_class = response_class

    async def app(request: Request) -> Response:
        try:
            body: Any = None
            if body_field:
                if is_body_form:
                    body = await request.form()
                else:
                    body_bytes = await request.body()
                    if body_bytes:
                        json_body: Any = Undefined
                        content_type_value = request.headers.get("content-type")
                        if not content_type_value:
                            json_body = await request.json()
                        else:
                            message = email.message.Message()
                            message["content-type"] = content_type_value
                            if message.get_content_maintype() == "application":
                                subtype = message.get_content_subtype()
                                if subtype == "json" or subtype.endswith("+json"):
                                    json_body = await request.json()
                        if json_body != Undefined:
                            body = json_body
                        else:
                            body = body_bytes
        except json.JSONDecodeError as e:
            raise RequestValidationError([ErrorWrapper(e, ("body", e.pos))], body=e.doc)
        except Exception as e:
            raise HTTPException(
                status_code=400, detail="There was an error parsing the body"
            ) from e
        solved_result = await solve_dependencies(
            request=request,
            dependant=dependant,
            body=body,
            dependency_overrides_provider=dependency_overrides_provider,
        )
        values, errors, background_tasks, sub_response, _ = solved_result
        if errors:
            raise RequestValidationError(errors, body=body)
        else:
            raw_response = await run_endpoint_function(
                dependant=dependant, values=values, is_coroutine=is_coroutine
            )

            if isinstance(raw_response, Response):
                if raw_response.background is None:
                    raw_response.background = background_tasks
                return raw_response

            response_args: Dict[str, Any] = {"background": background_tasks}
            # If status_code was set, use it, otherwise use the default from the
            # response class, in the case of redirect it's 307
            if status_code is not None:
                response_args["status_code"] = status_code

            if actual_response_class == FastJsonResponse:
                # FastJsonResponse bypasses response validation and jsonable_encoder
                response_data = raw_response
                response_args["include"] = response_model_include
                response_args["exclude"] = response_model_exclude
                response_args["by_alias"] = response_model_by_alias
                response_args["exclude_unset"] = response_model_exclude_unset
                response_args["exclude_defaults"] = response_model_exclude_defaults
                response_args["exclude_none"] = response_model_exclude_none
            else:
                response_data = await serialize_response(
                    field=response_field,
                    response_content=raw_response,
                    include=response_model_include,
                    exclude=response_model_exclude,
                    by_alias=response_model_by_alias,
                    exclude_unset=response_model_exclude_unset,
                    exclude_defaults=response_model_exclude_defaults,
                    exclude_none=response_model_exclude_none,
                    is_coroutine=is_coroutine,
                )
            response = actual_response_class(response_data, **response_args)
            response.headers.raw.extend(sub_response.headers.raw)
            if sub_response.status_code:
                response.status_code = sub_response.status_code
            return response

    return app

######


def apply_fastapi_tweaks():
    # Monkey patch Fast API
    utils.request_params_to_args = request_params_to_args
    routing.get_request_handler = get_request_handler
