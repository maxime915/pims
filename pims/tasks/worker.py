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

from cytomine import Cytomine

# Quick hack to avoid circular imports
try:
    from pims.application import app as _
except:  # noqa
    pass
# ----

from pims.api.exceptions import AuthenticationException
from pims.importer.importer import run_import as run_import_
from pims.tasks.celery_app import celery_app


@celery_app.task
def run_import_with_cytomine(cytomine_auth, filepath, name, cytomine_listener):
    with Cytomine(*cytomine_auth, configure_logging=False) as c:
        if not c.current_user:
            raise AuthenticationException("PIMS authentication to Cytomine failed.")

        run_import_(filepath, name, extra_listeners=[cytomine_listener])


@celery_app.task
def run_import(filepath, name):
    run_import_(filepath, name)
