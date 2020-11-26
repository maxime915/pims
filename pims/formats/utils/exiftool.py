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
import json
import subprocess


def is_valid_key(key):
    # https://exiftool.org/TagNames/Extra.html
    file_keys = ('FileName', 'Directory', 'FileSize', 'FileModifyDate', 'FileAccessDate', 'FileInodeChangeDate',
                 'FilePermissions', 'FileType', 'FileType', 'FileTypeExtension', 'MIMEType', 'ExifByteOrder')
    invalid_prefixes = ("ExifTool", "System", "SourceFile") + tuple("File:{}".format(k) for k in file_keys)
    for invalid_prefix in invalid_prefixes:
        if key.startswith(invalid_prefix):
            return False

    return True


def read_raw_metadata(path):
    bytes_info = "use -b option to extract)"

    exiftool_exc = "exiftool"
    exiftool_opts = ["-All", "-s", "-G", "-j", "-u", "-e"]
    args = [exiftool_exc] + exiftool_opts + [str(path)]
    result = subprocess.run(args, capture_output=True)
    if result.returncode == 0:
        metadata = json.loads(result.stdout)
        if type(metadata) == list and len(metadata) > 0:
            metadata = metadata[0]
        if type(metadata) != dict:
            return dict()
        return {
            k.replace(":", "."): v.strip() if type(v) == str else v
            for k, v in metadata.items()
            if is_valid_key(k) and bytes_info not in str(v)
        }

    return dict()
