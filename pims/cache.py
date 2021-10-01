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
import asyncio
import hashlib
import inspect
import typing
from enum import Enum
from functools import wraps, partial
from typing import Type, Callable, Optional

from fastapi_cache import FastAPICache, Coder
from fastapi_cache.backends import Backend
from fastapi_cache.backends.redis import RedisBackend as RedisBackend_
from fastapi_cache.coder import PickleCoder
from starlette.concurrency import run_in_threadpool
from starlette.responses import Response

from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES

HEADER_CACHE_CONTROL = "Cache-Control"
HEADER_ETAG = "ETag"
HEADER_IF_NONE_MATCH = "If-None-Match"


def get_cache() -> Backend:
    return FastAPICache.get_backend()


class RedisBackend(RedisBackend_):
    async def exists(self, key) -> bool:
        return await self.redis.exists(key)


async def exec_func_async(func, *args, **kwargs):
    is_async = asyncio.iscoroutinefunction(func)
    if is_async:
        return await func(*args, **kwargs)
    else:
        return await run_in_threadpool(func, *args, **kwargs)


def all_kwargs_key_builder(func, kwargs, excluded_parameters, prefix):
    copy_kwargs = kwargs.copy()
    for excluded in excluded_parameters:
        if excluded in copy_kwargs:
            copy_kwargs.pop(excluded)

    hashable = f"{func.__module__}:{func.__name__}"
    for k, v in copy_kwargs.items():
        if isinstance(v, Enum):
            v = v.value
        hashable += f":{k}={str(v)}"

    hashed = hashlib.md5(hashable.encode()).hexdigest()
    cache_key = f"{prefix}:{hashed}"
    return cache_key


def _image_response_key_builder(
        func, kwargs, excluded_parameters, prefix, supported_mimetypes
):
    copy_kwargs = kwargs.copy()
    headers = copy_kwargs.get('headers')
    if headers and 'headers' not in excluded_parameters:
        # Find true output extension
        accept = headers.get('accept')
        extension = copy_kwargs.get('extension')
        format = get_output_format(extension, accept, supported_mimetypes)
        copy_kwargs['extension'] = format

        # Extract other custom headers
        extra_headers = ('safe_mode', 'annotation_origin')
        for eh in extra_headers:
            v = headers.get(eh)
            if v:
                copy_kwargs[f"headers.{eh}"] = v
        del copy_kwargs['headers']

    return all_kwargs_key_builder(
        func, copy_kwargs, excluded_parameters, prefix
    )


def default_cache_control_builder(ttl=0):
    params = ["private", "must-revalidate"]
    if ttl:
        params += [f"max-age={ttl}"]
    return ','.join(params)


def cache(
        expire: int = None,
        vary: Optional[typing.List] = None,
        codec: Type[Coder] = None,
        key_builder: Callable = None,
        cache_control_builder: Callable = None
):
    def wrapper(func: Callable):
        @wraps(func)
        async def inner(*args, **kwargs):
            nonlocal expire
            nonlocal vary
            nonlocal codec
            nonlocal key_builder
            nonlocal cache_control_builder
            signature = inspect.signature(func)
            bound_args = signature.bind_partial(*args, **kwargs)
            bound_args.apply_defaults()
            all_kwargs = bound_args.arguments
            request = all_kwargs.pop("request", None)
            response = all_kwargs.pop("response", None)

            if request \
                    and request.headers.get(HEADER_CACHE_CONTROL) == "no-store":
                return exec_func_async(func, *args, **kwargs)

            expire = expire or FastAPICache.get_expire()
            codec = codec or FastAPICache.get_coder()
            key_builder = key_builder or FastAPICache.get_key_builder()
            backend = FastAPICache.get_backend()
            prefix = FastAPICache.get_prefix()

            cache_key = key_builder(func, all_kwargs, vary, prefix)
            ttl, encoded = await backend.get_with_ttl(cache_key)
            if not request:
                if encoded is not None:
                    return codec.decode(encoded)
                data = await exec_func_async(func, *args, **kwargs)
                encoded = codec.encode(data)
                await backend.set(
                    cache_key, encoded,
                    expire or FastAPICache.get_expire()
                )
                return data

            if_none_match = request.headers.get(HEADER_IF_NONE_MATCH.lower())
            if encoded is not None:
                if response:
                    cache_control_builder = \
                        cache_control_builder or default_cache_control_builder
                    response.headers[HEADER_CACHE_CONTROL] = \
                        cache_control_builder(ttl=ttl)
                    etag = f"W/{hash(encoded)}"
                    response.headers[HEADER_ETAG] = etag
                    if if_none_match == etag:
                        response.status_code = 304
                        return response
                decoded = codec.decode(encoded)
                if isinstance(decoded, Response):
                    decoded.headers[HEADER_CACHE_CONTROL] = \
                        response.headers.get(HEADER_CACHE_CONTROL)
                    decoded.headers[HEADER_ETAG] = \
                        response.headers.get(HEADER_ETAG)
                return decoded

            data = await exec_func_async(func, *args, **kwargs)
            encoded = codec.encode(data)
            await backend.set(cache_key, encoded, expire)

            if response:
                cache_control_builder = \
                    cache_control_builder or default_cache_control_builder
                response.headers[HEADER_CACHE_CONTROL] = \
                    cache_control_builder(ttl=expire)
                etag = f"W/{hash(encoded)}"
                response.headers[HEADER_ETAG] = etag
                if isinstance(data, Response):
                    data.headers[HEADER_CACHE_CONTROL] = \
                        response.headers.get(HEADER_CACHE_CONTROL)
                    data.headers[HEADER_ETAG] = \
                        response.headers.get(HEADER_ETAG)

            return data

        return inner

    return wrapper


def cache_image_response(
        expire: int = None,
        vary: Optional[typing.List] = None,
        supported_mimetypes=None
):
    if supported_mimetypes is None:
        supported_mimetypes = VISUALISATION_MIMETYPES
    key_builder = partial(
        _image_response_key_builder, supported_mimetypes=supported_mimetypes
    )
    codec = PickleCoder
    return cache(expire, vary, codec, key_builder)
