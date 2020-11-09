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

import os
import time
from logging.config import dictConfig

from colors import colors

import connexion
from flask import g, request

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s][%(threadName)s] %(levelname)s in %(name)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
})


def create_app(test_config=None):
    if os.environ.get("PIMS_SETTINGS"):
        CONFIG_FILE = os.environ.get("PIMS_SETTINGS")
    else:
        here = os.path.abspath(os.path.dirname(__file__))
        CONFIG_FILE = os.path.join(os.path.abspath(os.path.join(here, os.pardir)), "app-config.cfg")

    app = connexion.FlaskApp(__name__, specification_dir='openapi/', options={'swagger_url': '/docs'})
    api = app.add_api('api-specification.yaml')
    flask_app = app.app
    flask_app.config.from_pyfile(CONFIG_FILE)

    if test_config is not None:
        flask_app.config.from_mapping(test_config)

    flask_app.config['api_version'] = api.specification.raw['info']['version']

    @flask_app.before_request
    def start_timer():
        g.start = time.time()

    @flask_app.after_request
    def log_request(response):
        now = time.time()
        duration = round(now - g.start, 4)
        host = request.host.split(':', 1)[0]
        args = dict(request.args)
        values = dict(request.values)

        log_params = [
            ('method', request.method, 'magenta'),
            ('path', request.path, 'blue'),
            ('status', response.status_code, 'yellow'),
            ('duration', "{}s".format(duration), 'green'),
            ('host', host, 'red'),
            ('params', args, 'blue'),
            ('values', values, 'blue')
        ]

        parts = []
        for name, value, color in log_params:
            part = colors.color("{}".format(value), fg=color)
            parts.append(part)
        line = " ".join(parts)
        flask_app.logger.info(line)

        return response

    return flask_app
