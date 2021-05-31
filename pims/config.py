from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    root: str

    class Config:
        env_file = "pims-config.env"
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings():
    return Settings()
