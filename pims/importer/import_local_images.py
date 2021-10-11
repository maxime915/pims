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
import logging
import shutil
import sys
from argparse import ArgumentParser

from pims.files.file import Path
from pims.importer.importer import PENDING_PATH, run_import

logging.basicConfig()
logger = logging.getLogger("upload")
logger.setLevel(logging.INFO)


# Run me with: CONFIG_FILE=/path/to/config.env python import_local_images.py --path /my/folder
if __name__ == '__main__':
    parser = ArgumentParser(prog="Import images sequentially to PIMS root from a local folder.")
    parser.add_argument('--path', help="A directory with images to import, or an image path.")

    params, _ = parser.parse_known_args(sys.argv[1:])
    path = Path(params.path)

    if not path.exists():
        exit(-1)

    if path.is_file():
        image_paths = [path]
    else:
        image_paths = [p for p in path.recursive_iterdir() if p.is_file()]

    for image_path in image_paths:
        # We have to copy to file to pending path first to pass importer validation.
        tmp_path = Path(PENDING_PATH) / image_path.name
        shutil.copy(image_path, tmp_path)
        try:
            run_import(tmp_path, image_path.name, prefer_copy=False)
        except Exception:  # noqa
            tmp_path.unlink(missing_ok=True)
