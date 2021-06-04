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
import traceback

from cytomine import Cytomine
from cytomine.models import Storage, ProjectCollection, Project, UploadedFile, ImageInstance
from flask import current_app

from pims.api.exceptions import CytomineProblem, AuthenticationException
from pims.api.utils.cytomine_auth import parse_authorization_header, parse_request_token, sign_token, \
    get_this_image_server
from pims.api.utils.image_parameter import ensure_list
from pims.files.file import Path
from pims.importer.importer import FileImporter
from pims.importer.logger import CytomineListener, StdoutListener


def import_(filepath, body):
    pass


def legacy_import(body, core=None, cytomine=None, storage=None, idStorage=None, projects=None, idProject=None,
                  sync=False, keys=None, values=None):
    core = cytomine if cytomine is not None else core
    id_storage = idStorage if idStorage is not None else storage
    id_projects = idProject.split(",") if idProject and len(idProject) > 0 else projects

    upload_name = body['filesname']
    upload_path = body['filespath']
    upload_size = body['filessize']
    upload_content_type = body['filescontent_type']

    public_key, signature = parse_authorization_header()
    with Cytomine.connect(core, current_app.config['CYTOMINE_PUBLIC_KEY'],
                          current_app.config['CYTOMINE_PRIVATE_KEY']) as c:
        this = get_this_image_server()
        keys = c.get("userkey/{}/keys.json".format(public_key))
        private_key = keys["privateKey"]

        if sign_token(private_key, parse_request_token()) != signature:
            raise AuthenticationException("Authentication to Cytomine failed")

        c.set_credentials(public_key, private_key)
        user = c.current_user
        storage = Storage().fetch(id_storage)
        if not storage:
            raise CytomineProblem("Storage {} not found".format(id_storage))

        id_projects = ensure_list(id_projects)
        projects = ProjectCollection()
        for id in id_projects:
            project = Project().fetch(id)
            if not project:
                raise CytomineProblem("Project {} not found".format(id))
            projects.append(project)

        # TODO: keys/values

        root = UploadedFile(upload_name, upload_path, upload_size, "", upload_content_type,
                            id_projects, id_storage, user.id, this.id, UploadedFile.UPLOADED).save()

        # TODO: async mode
        try:
            root, images = _legacy_import(upload_path, upload_name, root, projects)
            return [{
                "status": 200,
                "name": upload_name,
                "uploadedFile": root,
                "images": [{
                    "image": image[0],
                    "imageInstances": image[1]
                } for image in images]
            }]
        except Exception as e:
            traceback.print_exc()
            return [{
                "status": 500,
                "error": str(e),
                "files": [{
                    "name": upload_name,
                    "size": 0,
                    "error": str(e)
                }]
            }], 400


def _legacy_import(filepath, name, root_uf, projects):
    pending_file = Path(filepath)
    cytomine = CytomineListener(root_uf.id, root_uf.id)
    listeners = [
        cytomine,
        StdoutListener(name)
    ]

    fi = FileImporter(pending_file, name, listeners)
    fi.run()

    images = []
    for ai in cytomine.abstract_images:
        instances = []
        for p in projects:
            instances.append(ImageInstance(ai.id, p.id).save())
        images.append((ai, instances))

    return root_uf.fetch(), images


def export(filepath):
    pass


def delete(filepath):
    pass
