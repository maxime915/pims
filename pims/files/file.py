from datetime import datetime
from pathlib import Path as _Path

PROCESSED_DIR = "processed"
EXTRACTED_DIR = "extracted"

UPLOAD_DIR_PREFIX = "upload"
EXTRACTED_FILE_DIR_PREFIX = "file"

ORIGINAL_STEM = "original"
SPATIAL_STEM = "visualisation"
SPECTRAL_STEM = "spectral"


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
        return Image(original) if original else None

    def get_spatial(self):
        if not self.processed_root().exists():
            return None

        return next((child for child in self.processed_root().iterdir() if child.has_spatial_role()), None)

    def get_spectral(self):
        if not self.processed_root().exists():
            return None

        return next((child for child in self.processed_root().iterdir() if child.has_spectral_role()), None)

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
