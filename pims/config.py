import os
import logging

from functools import lru_cache

from pydantic import BaseSettings

logger = logging.getLogger("pims.app")


class Settings(BaseSettings):
    root: str
    pending_path: str
    default_image_size_safety_mode: str = "SAFE_REJECT"
    default_annotation_origin: str = "LEFT_TOP"
    output_size_limit: int = 10000
    pims_url: str = "http://localhost-ims"

    cache_url: str = "http://pims-cache:6379"
    cache_ttl_thumb: int = 60 * 60 * 24 * 15

    cytomine_public_key: str
    cytomine_private_key: str

    class Config:
        env_file = "pims-config.env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings():
    env_file = os.getenv('CONFIG_FILE', 'pims-config.env')
    logger.info(f"[green]Loading config from {env_file}")
    return Settings(_env_file=env_file)
