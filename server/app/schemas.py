from typing import Literal

from pydantic import BaseModel, Field


class ClientInitRequest(BaseModel):
    app: str = Field(min_length=1)
    version: str = Field(min_length=1)
    client_id: str = Field(min_length=1, max_length=128)
    os: str = Field(min_length=1)
    os_version: str = Field(min_length=1)
    arch: str = Field(min_length=1)
    locale: str = Field(min_length=1)
    event: Literal["startup"]


class ClientInitResponse(BaseModel):
    version: str
    minimum_supported_version: str
    download_url: str
    release_notes_url: str
    message: str
    severity: Literal["optional", "recommended", "required"]
