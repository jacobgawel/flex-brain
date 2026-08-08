import uuid

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    model: str | None = None
    document_id: str | None = Field(
        default=None, description="restrict the search to one ingested document"
    )


class SearchHit(BaseModel):
    id: uuid.UUID
    score: float
    document_id: str
    filename: str | None
    mimetype: str
    chunk_index: int


class SearchResponse(BaseModel):
    model: str
    hits: list[SearchHit]
