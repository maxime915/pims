from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    root: str
    default_image_size_safety_mode: str = "SAFE_REJECT"
    default_annotation_origin: str = "LEFT_TOP"
    output_size_limit: int = 10000
    pims_url: str = "http://localhost-ims"

    cytomine_public_key: str
    cytomine_private_key: str

    class Config:
        env_file = "pims-config.env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings():
    return Settings()
