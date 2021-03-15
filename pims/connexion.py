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
import collections
import copy
import functools
import logging

from connexion.decorators.uri_parsing import OpenAPIURIParser
from connexion.decorators.validation import TYPE_MAP, TypeValidationError, _jsonschema_3_or_newer, \
    validate_parameter_list
from connexion.exceptions import ExtraParameterProblem, BadRequestProblem
from connexion.operations import OpenAPIOperation
from connexion.utils import is_nullable, is_null, deep_merge
from jsonschema import draft4_format_checker, ValidationError
from jsonschema.validators import extend, Draft4Validator
from werkzeug.datastructures import FileStorage

logger = logging.getLogger("connexion.custom")


def _get_val_from_param(self, value, query_defn):
    try:
        return coerce_type(query_defn, value)
    except TypeValidationError as e:
        return str(e)


def _get_query_defaults(self, query_defns):
    defaults = {}
    for k, v in query_defns.items():
        try:
            if "x-default" in v['schema']:
                defaults[k] = v["schema"]["x-default"]
            elif v["schema"]["type"] == "object":
                defaults[k] = self._get_default_obj(v["schema"])
            else:
                defaults[k] = v["schema"]["default"]

            if v["schema"].get('x-single-or-array') and type(defaults[k]) != list:
                defaults[k] = [defaults[k]]
        except KeyError:
            pass
    return defaults


def _get_body_argument(self, body, arguments, has_kwargs, sanitize):
    body_schema = merge_allof(copy.deepcopy(self.body_schema))
    x_body_name = sanitize(body_schema.get('x-body-name', 'body'))
    if is_nullable(body_schema) and is_null(body):
        return {x_body_name: None}

    default_body = body_schema.get('default', {})

    # by OpenAPI specification `additionalProperties` defaults to `true`
    # see: https://github.com/OAI/OpenAPI-Specification/blame/3.0.2/versions/3.0.2.md#L2305
    # BUT do not allow by default to simplify PIMS implementation
    additional_props = body_schema.get("additionalProperties", False)

    if body is None:
        body = copy.deepcopy(default_body)

    if body_schema.get("oneOf"):
        keys = body.keys()
        for oneof_schema in body_schema.get("oneOf"):
            # TODO: better schema discrimination. Currently, discrimination is done with required props.
            required = oneof_schema.get("required", [])
            if all(k in keys for k in required):
                body_schema = oneof_schema
                break

    if body_schema.get("type") != "object":
        if x_body_name in arguments or has_kwargs:
            return {x_body_name: body}
        return {}

    body_arg = copy.deepcopy(default_body)
    body_arg.update(copy.deepcopy(self._get_default_obj(body_schema)))
    body_arg.update(body or {})

    res = {}
    body_props = {k: {"schema": v} for k, v
                  in body_schema.get("properties", {}).items()}
    if body_props or additional_props:
        res = self._get_typed_body_values(body_arg, body_props, additional_props)

    if x_body_name in arguments or has_kwargs:
        return {x_body_name: res}
    return {}

# Monkey patching
OpenAPIOperation._get_val_from_param = _get_val_from_param
OpenAPIOperation._get_query_defaults = _get_query_defaults
OpenAPIOperation._get_body_argument = _get_body_argument


class PIMSOpenAPIURIParser(OpenAPIURIParser):
    def resolve_params(self, params, _in):
        """
        takes a dict of parameters, and resolves the values into
        the correct array type handling duplicate values, and splitting
        based on the collectionFormat defined in the spec.
        """
        resolved_param = {}
        for k, values in params.items():
            param_defn = self.param_defns.get(k)
            param_schema = self.param_schemas.get(k)

            if not (param_defn or param_schema):
                # rely on validation
                resolved_param[k] = values
                continue

            if _in == 'path':
                # multiple values in a path is impossible
                values = [values]

            if param_schema is not None \
                    and (param_schema.get('type') == 'array' or param_schema.get('x-single-or-array')):
                # resolve variable re-assignment, handle explode
                values = self._resolve_param_duplicates(values, param_defn, _in)
                # handle array styles
                resolved_param[k] = self._split(values, param_defn, _in)
            else:
                resolved_param[k] = values[-1]

        return resolved_param


def merge_allof(schema):
    if 'allOf' in schema:
        merged = dict()
        for item in schema['allOf']:
            merged = deep_merge(merged, merge_allof(item))
        return merged
    elif 'oneOf' in schema:
        schema['oneOf'] = [merge_allof(s) for s in schema['oneOf']]
        return schema
    elif 'items' in schema:
        schema['items'] = merge_allof(schema['items'])
        return schema
    else:
        return schema


def coerce_type(param, value, parameter_type=None, parameter_name=None):
    def make_type(value, type_literal):
        type_func = TYPE_MAP.get(type_literal)
        return type_func(value)

    param_schema = merge_allof(copy.deepcopy(param.get("schema", param)))
    if is_nullable(param_schema) and is_null(value):
        return None

    errors = []
    params_schemas = param_schema['oneOf'] if 'oneOf' in param_schema else [param_schema]
    for param_schema in params_schemas:
        param_type = param_schema.get('type')
        parameter_name = parameter_name if parameter_name else param.get('name')
        if param_type == "array":
            converted_params = []
            for v in value:
                try:
                    converted = make_type(v, param_schema["items"]["type"])
                except KeyError:
                    converted = v
                    for one_of_schema in param_schema["items"]["oneOf"]:
                        try:
                            converted = make_type(v, one_of_schema["type"])
                            break
                        except (ValueError, TypeError):
                            continue
                except (ValueError, TypeError):
                    converted = v
                converted_params.append(converted)
            return converted_params
        elif param_type == 'object':
            if param_schema.get('properties'):
                def cast_leaves(d, schema):
                    if type(d) is not dict:
                        try:
                            return make_type(d, schema['type'])
                        except (ValueError, TypeError):
                            return d
                    for k, v in d.items():
                        if k in schema['properties']:
                            d[k] = cast_leaves(v, schema['properties'][k])
                    return d

                return cast_leaves(value, param_schema)
            return value
        else:
            try:
                return make_type(value, param_type)
            except ValueError:
                errors.append(TypeValidationError(param_type, parameter_type, parameter_name))
                continue
            except TypeError:
                continue

    if "string" in [param_schema.get('type') for param_schema in params_schemas]:
        return str(value)

    if len(errors) > 0:
        raise errors[-1]

    return value


class PIMSParameterValidator(object):
    def __init__(self, parameters, api, strict_validation=False):
        """
        :param parameters: List of request parameter dictionaries
        :param api: api that the validator is attached to
        :param strict_validation: Flag indicating if parameters not in spec are allowed
        """
        self.parameters = collections.defaultdict(list)
        for p in parameters:
            self.parameters[p['in']].append(p)

        self.api = api
        self.strict_validation = strict_validation

    @staticmethod
    def validate_parameter(parameter_type, value, param, param_name=None):
        if value is not None:
            if is_nullable(param) and is_null(value):
                return

            try:
                converted_value = coerce_type(param, value, parameter_type, param_name)
            except TypeValidationError as e:
                return str(e)

            param = copy.deepcopy(param)
            param = param.get('schema', param)
            if 'required' in param:
                del param['required']
            try:
                if parameter_type == 'formdata' and param.get('type') == 'file':
                    if _jsonschema_3_or_newer:
                        extend(
                            Draft4Validator,
                            type_checker=Draft4Validator.TYPE_CHECKER.redefine(
                                "file",
                                lambda checker, instance: isinstance(instance, FileStorage)
                            )
                        )(param, format_checker=draft4_format_checker).validate(converted_value)
                    else:
                        Draft4Validator(
                            param,
                            format_checker=draft4_format_checker,
                            types={'file': FileStorage}).validate(converted_value)
                else:
                    Draft4Validator(
                        param, format_checker=draft4_format_checker).validate(converted_value)
            except ValidationError as exception:
                debug_msg = 'Error while converting value {converted_value} from param ' \
                            '{type_converted_value} of type real type {param_type} to the declared type {param}'
                fmt_params = dict(
                    converted_value=str(converted_value),
                    type_converted_value=type(converted_value),
                    param_type=param.get('type'),
                    param=param
                )
                logger.info(debug_msg.format(**fmt_params))
                return str(exception)

        elif param.get('required'):
            return "Missing {parameter_type} parameter '{param[name]}'".format(**locals())

    def validate_query_parameter_list(self, request):
        request_params = request.query.keys()
        spec_params = [x['name'] for x in self.parameters.get('query', [])]
        return validate_parameter_list(request_params, spec_params)

    def validate_formdata_parameter_list(self, request):
        request_params = request.form.keys()
        try:
            spec_params = [x['name'] for x in self.parameters['formData']]
        except KeyError:
            # OAS 3
            return set()
        return validate_parameter_list(request_params, spec_params)

    def validate_query_parameter(self, param, request):
        """
        Validate a single query parameter (request.args in Flask)

        :type param: dict
        :rtype: str
        """
        val = request.query.get(param['name'])
        return self.validate_parameter('query', val, param)

    def validate_path_parameter(self, param, request):
        val = request.path_params.get(param['name'].replace('-', '_'))
        return self.validate_parameter('path', val, param)

    def validate_header_parameter(self, param, request):
        val = request.headers.get(param['name'])
        return self.validate_parameter('header', val, param)

    def validate_cookie_parameter(self, param, request):
        val = request.cookies.get(param['name'])
        return self.validate_parameter('cookie', val, param)

    def validate_formdata_parameter(self, param_name, param, request):
        if param.get('type') == 'file' or param.get('format') == 'binary':
            val = request.files.get(param_name)
        else:
            val = request.form.get(param_name)

        return self.validate_parameter('formdata', val, param)

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        @functools.wraps(function)
        def wrapper(request):
            logger.debug("%s validating parameters...", request.url)

            if self.strict_validation:
                query_errors = self.validate_query_parameter_list(request)
                formdata_errors = self.validate_formdata_parameter_list(request)

                if formdata_errors or query_errors:
                    raise ExtraParameterProblem(formdata_errors, query_errors)

            for param in self.parameters.get('query', []):
                error = self.validate_query_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('path', []):
                error = self.validate_path_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('header', []):
                error = self.validate_header_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('cookie', []):
                error = self.validate_cookie_parameter(param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            for param in self.parameters.get('formData', []):
                error = self.validate_formdata_parameter(param["name"], param, request)
                if error:
                    raise BadRequestProblem(detail=error)

            return function(request)

        return wrapper
