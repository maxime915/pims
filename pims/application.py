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

import logging
logger = logging.getLogger("pims")
logger.info("[green bold]PIMS initialization...")

import time
from fastapi import FastAPI, Request
from pydantic import ValidationError

from pims.config import get_settings
from pims.docs import get_redoc_html
from .api.exceptions import add_problem_exception_handler
from .api import server, housekeeping, formats, metadata, thumb, window, resized, annotation, tile, operations
from . import __api_version__


app = FastAPI(
    title="Cytomine Python Image Management Server PIMS",
    description="Cytomine Python Image Management Server (PIMS) HTTP API. "
                "While this API is intended to be internal, a lot of the "
                "following specification can be ported to the "
                "external (public) Cytomine API.",
    version=__api_version__,
    docs_url=None,
    redoc_url=None,
)


@app.on_event("startup")
async def startup():
    # Check PIMS configuration
    try:
        settings = get_settings()
        logger.info("[green bold]PIMS is starting with config:[/]")
        for k, v in settings.dict().items():
            logger.info(f"[green]* {k}:[/] [blue]{v}[/]", extra={"highlight": False})
    except ValidationError as e:
        logger.error("Impossible to read or parse some PIMS settings:")
        logger.error(e)

    # Check optimisation are enabled for external libs
    from pydantic import compiled as pydantic_compiled
    if not pydantic_compiled:
        logger.warning(f"[red]Pydantic is running in non compiled mode.")

    from pyvips import API_mode as pyvips_binary
    if not pyvips_binary:
        logger.warning("[red]Pyvips is running in non binary mode.")

    from shapely.speedups import enabled as shapely_speedups
    if not shapely_speedups:
        logger.warning("[red]Shapely is running without speedups.")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()

    response = await call_next(request)

    now = time.time()
    duration = (now - start) * 1000
    args = dict(request.query_params)

    log_params = [
        ('method', request.method, 'magenta'),
        ('path', request.url.path, 'blue'),
        ('status', response.status_code, 'yellow'),
        ('duration', f"{duration:.2f}ms", 'green'),
        ('params', args, 'blue'),
    ]

    parts = []
    for name, value, color in log_params:
        parts.append(f"[{color}]{value}[/]")
    line = " ".join(parts)
    logger.info(line, extra={"highlight": False})

    return response


@app.get("/docs", include_in_schema=False)
def docs(req: Request):
    root_path = req.scope.get("root_path", "").rstrip("/")
    openapi_url = root_path + app.openapi_url
    return get_redoc_html(openapi_url=openapi_url, title=app.title)


app.include_router(metadata.router)
app.include_router(tile.router)
app.include_router(thumb.router)
app.include_router(resized.router)
app.include_router(window.router)
app.include_router(annotation.router)
app.include_router(formats.router)
app.include_router(operations.router)
app.include_router(housekeeping.router)
app.include_router(server.router)

add_problem_exception_handler(app)
