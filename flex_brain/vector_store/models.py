import uuid

from pydantic import BaseModel


class DocumentPayload(BaseModel):
    document_id: str
    filename: str | None
    mimetype: str
    chunk_index: int
    model: str


class VectorRecord(BaseModel):
    id: uuid.UUID
    vector: list[float]
    payload: DocumentPayload


class SearchResult(BaseModel):
    id: uuid.UUID
    score: float
    payload: DocumentPayload
