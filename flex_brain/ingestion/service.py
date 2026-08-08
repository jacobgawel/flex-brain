import hashlib
import uuid
from dataclasses import dataclass

from google.genai import types

from flex_brain.constants import DEFAULT_EMBEDDING_MODEL, POINT_NAMESPACE
from flex_brain.embedding import EmbeddingService
from flex_brain.ingestion.mimetype import detect_mimetype
from flex_brain.ingestion.pdf import validate_pdf
from flex_brain.vector_store import VectorStoreService
from flex_brain.vector_store.models import DocumentPayload, VectorRecord

MAX_PDF_PAGES = 6

TEXT_MIMETYPES = {"application/json", "application/xml", "application/x-yaml"}

# binary mimetypes gemini-embedding-2 embeds natively; per-request model
# limits apply (6 images, 180s audio, 6-page PDF, 8192 tokens total)
MULTIMODAL_MIMETYPES = {
    "image/png",
    "image/jpeg",
    "audio/mpeg",
    "audio/wav",
    "application/pdf",
}


class UnsupportedMimetypeError(Exception):
    def __init__(self, mimetype: str):
        self.mimetype = mimetype
        super().__init__(f"unsupported mimetype: {mimetype}")


@dataclass
class IngestionResult:
    document_id: str
    mimetype: str
    chunks: int


class IngestionService:
    """ingestion service for processing data"""

    def __init__(
        self, embedding_service: EmbeddingService, vector_store: VectorStoreService
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def ingest(
        self,
        content: bytes,
        filename: str | None = None,
        declared_type: str | None = None,
        model: str | None = None,
    ) -> IngestionResult:
        if model is None:
            model = DEFAULT_EMBEDDING_MODEL

        mimetype = detect_mimetype(content, filename, declared_type)

        part = self._to_embeddable(content, mimetype)

        embeddings = await self.embedding_service.embed(part, model)

        # content-addressed identity: same bytes -> same ids -> re-ingestion
        # overwrites existing points instead of duplicating them
        document_id = hashlib.sha256(content).hexdigest()

        records = [
            VectorRecord(
                id=uuid.uuid5(POINT_NAMESPACE, f"{document_id}:{index}"),
                vector=vector,
                payload=DocumentPayload(
                    document_id=document_id,
                    filename=filename,
                    mimetype=mimetype,
                    chunk_index=index,
                    model=model,
                ),
            )
            for index, vector in enumerate(embeddings)
        ]

        await self.vector_store.upsert(records)

        return IngestionResult(
            document_id=document_id, mimetype=mimetype, chunks=len(records)
        )

    def _to_embeddable(self, content: bytes, mimetype: str) -> str | types.Part:
        if mimetype.startswith("text/") or mimetype in TEXT_MIMETYPES:
            return content.decode("utf-8", errors="replace")

        if mimetype in MULTIMODAL_MIMETYPES:
            if mimetype == "application/pdf":
                validate_pdf(content, MAX_PDF_PAGES)
            return types.Part.from_bytes(data=content, mime_type=mimetype)

        raise UnsupportedMimetypeError(mimetype)
