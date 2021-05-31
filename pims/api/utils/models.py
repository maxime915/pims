from pydantic import BaseModel, Field, conint


class CollectionSize(BaseModel):
    size: int = Field(..., description='The collection size')


class FormatId(BaseModel):
    __root__: str = Field(..., description='Unique format identifier', example='VMS')


class ZoomOrLevel(BaseModel):
    __root__: conint(ge=0) = Field(..., example=0)