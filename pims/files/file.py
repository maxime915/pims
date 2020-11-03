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
    @property
    def creation_datetime(self):
        return datetime.fromtimestamp(self.stat().st_ctime)

    @property
    def size(self):
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

    def get_original(self):
        return next([child for child in self.upload_root().recursive_iterdir() if child.has_original_role()], None)

    def get_spatial(self):
        return next([child for child in self.upload_root().recursive_iterdir() if child.has_spatial_role()], None)

    def get_spectral(self):
        return next([child for child in self.upload_root().recursive_iterdir() if child.has_spectral_role()], None)

    def is_collection(self):
        # is there a "extracted" directory in upload root children ?
        if not self.is_extracted():
            for child in self.upload_root().recursive_iterdir():
                if child.is_extracted():
                    return True
        return False

    def is_single(self):
        return not self.is_collection()
