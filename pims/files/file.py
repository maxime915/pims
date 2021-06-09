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

import shutil
from datetime import datetime
from pathlib import Path as _Path

from pims.formats.utils.factories import FormatFactory, SpatialReadableFormatFactory, SpectralReadableFormatFactory

PROCESSED_DIR = "processed"
EXTRACTED_DIR = "extracted"

UPLOAD_DIR_PREFIX = "upload"
EXTRACTED_FILE_DIR_PREFIX = "file"

ORIGINAL_STEM = "original"
SPATIAL_STEM = "visualisation"
SPECTRAL_STEM = "spectral"
HISTOGRAM_STEM = "histogram"

_NUM_SIGNATURE_BYTES = 262


class Path(type(_Path()), _Path):
    def __init__(self, *pathsegments):
        self._pathsegments = pathsegments
        super().__init__()

    @property
    def creation_datetime(self):
        return datetime.fromtimestamp(self.stat().st_ctime)

    @property
    def size(self):
        if self.is_dir():
            return sum([it.size for it in self.iterdir()])

        return self.stat().st_size

    @property
    def extension(self):
        return ''.join(self.suffixes)

    @property
    def true_stem(self):
        return self.stem.split('.')[0]

    def mount_point(self):
        for parent in self.parents:
            if parent.is_mount():
                return parent
        return None

    def mount_disk_usage(self):
        return shutil.disk_usage(self)

    def recursive_iterdir(self):
        for p in self.rglob("**/*"):
            yield p

    def is_processed(self):
        return PROCESSED_DIR in self.parts

    def is_extracted(self):
        return EXTRACTED_DIR in self.parts

    def has_upload_role(self):
        return not self.is_processed() and self.parent.samefile(self.upload_root()) and self.is_file()

    def has_original_role(self):
        return self.is_processed() and self.true_stem == ORIGINAL_STEM

    def has_spatial_role(self):
        return self.is_processed() and self.true_stem == SPATIAL_STEM

    def has_spectral_role(self):
        return self.is_processed() and self.true_stem == SPECTRAL_STEM

    def has_histogram_role(self):
        return self.is_processed() and self.true_stem == HISTOGRAM_STEM

    def upload_root(self):
        for parent in self.parents:
            if parent.name.startswith(UPLOAD_DIR_PREFIX):
                return parent
        raise FileNotFoundError("No upload root for {}".format(self))

    def processed_root(self):
        processed = self.upload_root() / Path(PROCESSED_DIR)
        return processed

    def extracted_root(self):
        extracted = self.processed_root() / Path(EXTRACTED_DIR)
        return extracted

    def get_upload(self):
        upload = next((child for child in self.upload_root().iterdir() if child.has_upload_role()), None)
        return upload

    def get_original(self):
        if not self.processed_root().exists():
            return None

        original = next((child for child in self.processed_root().iterdir() if child.has_original_role()), None)

        from pims.files.image import Image
        return Image(original, factory=FormatFactory()) if original else None

    def get_spatial(self):
        if not self.processed_root().exists():
            return None

        spatial = next((child for child in self.processed_root().iterdir() if child.has_spatial_role()), None)

        from pims.files.image import Image
        return Image(spatial, factory=SpatialReadableFormatFactory()) if spatial else None

    def get_spectral(self):
        if not self.processed_root().exists():
            return None

        spectral = next((child for child in self.processed_root().iterdir() if child.has_spectral_role()), None)

        from pims.files.image import Image
        return Image(spectral, factory=SpectralReadableFormatFactory()) if spectral else None

    def get_histogram(self):
        if not self.processed_root().exists():
            return None

        histogram = next((child for child in self.processed_root().iterdir() if child.has_histogram_role()), None)
        if histogram:
            from pims.formats.utils.histogram import FileHistogram
            return FileHistogram(histogram)
        return None


    def get_representations(self):
        representations = [self.get_upload(), self.get_original(), self.get_spatial(), self.get_spectral()]
        return [representation for representation in representations if representation is not None]

    def get_representation(self, role):
        if role == "UPLOAD":
            return self.get_upload()
        elif role == "ORIGINAL":
            return self.get_original()
        elif role == "SPATIAL":
            return self.get_spatial()
        elif role == "SPECTRAL":
            return self.get_spectral()
        else:
            return None

    def get_extracted_children(self):
        if not self.is_collection():
            return []

        return self.extracted_root().recursive_iterdir()

    def is_collection(self):
        if not self.processed_root().exists():
            return None

        # is there a "extracted" directory in upload root children ?
        if not self.is_extracted():
            for child in self.processed_root().iterdir():
                if child.is_extracted():
                    return True
        return False

    def is_single(self):
        return not self.is_collection()

    def signature(self):
        if not self.is_file():
            return []
        with self.resolve().open('rb') as fp:
            return bytearray(fp.read(_NUM_SIGNATURE_BYTES))
