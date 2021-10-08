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

from celery import Celery

from pims.config import get_settings

settings = get_settings()

broker_url = f"{settings.task_queue_user}:{settings.task_queue_password}@{settings.task_queue_url}"
celery_app = Celery(
    "worker",
    broker=f"amqp://{broker_url}//",
    backend=f"rpc://{broker_url}//"
)

celery_app.conf.update(
    task_serializer="pickle",
    result_serializer="pickle",
    accept_content=["pickle"]
)

celery_app.conf.task_routes = {
    "pims.tasks.worker.run_import": "pims-import-queue",
    "pims.tasks.worker.run_import_with_cytomine": "pims-import-queue",
}
