from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    root: str
    default_image_size_safety_mode: str = "SAFE_REJECT"
    default_annotation_origin: str = "LEFT_TOP"
    output_size_limit: int = 10000

    class Config:
        env_file = "pims-config.env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings():
    return Settings()
