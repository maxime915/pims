import logging
import time

import pint

from fastapi import FastAPI, Request
from colors import colors

from pims.docs import get_redoc_html
from .api.exceptions import add_problem_exception_handler
from .api import server, housekeeping, formats, metadata, thumb, window, resized, annotation, tile
from . import __api_version__


logger = logging.getLogger("pims")

UNIT_REGISTRY = pint.UnitRegistry()

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
        part = colors.color("{}".format(value), fg=color)
        parts.append(part)
    line = " ".join(parts)
    logger.info(line)

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
app.include_router(housekeeping.router)
app.include_router(server.router)

add_problem_exception_handler(app)


if __name__ == "__main__":
    import uvicorn

    log_format = "[%(asctime)s][%(threadName)s] %(levelname)s in %(name)s: %(message)s"
    log_config = {
        'version': 1,
        'formatters': {
            'default': {
                'format': log_format,
            }
        },
        'handlers': {
            'default': {
                'class': 'logging.StreamHandler',
                'formatter': 'default'
            }
        },
        'loggers': {
            '': {
                'level': 'DEBUG',
                'handlers': ['default'],
                'propagate': True
            },
            "pims": {
                "handlers": ["default"],
                "level": "DEBUG",
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            },
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {
                "handlers": ["default"],
                "level": "INFO",
                "propagate": False
            },
            'pyvips.voperation': {
                'level': 'INFO',
                'handlers': ['default'],
            },
            'pyvips.vobject': {
                'level': 'INFO',
                'handlers': ['default'],
            },
            'pyvips.error': {
                'level': 'INFO',
                'handlers': ['default'],
            }
        }
    }

    uvicorn.run("pims.main:app", host="0.0.0.0", port=5000,
                log_config=log_config, reload=True)
