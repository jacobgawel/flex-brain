from fastapi import UploadFile
from pydantic import BaseModel


class IngestionRequest(BaseModel):
    file: UploadFile
    model: str | None = None
    space_id: str | None = None


class IngestionResponse(BaseModel):
    document_id: str
    model: str
    filename: str | None
    mimetype: str
    chunks: int
    space_id: str | None
