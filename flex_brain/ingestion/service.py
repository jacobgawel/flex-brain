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


class EmptyContentError(Exception):
    def __init__(self):
        super().__init__("file has no embeddable content")


@dataclass
class IngestionResult:
    document_id: str
    mimetype: str
    chunks: int
    space_id: str | None = None


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
        space_id: str | None = None,
    ) -> IngestionResult:
        if model is None:
            model = DEFAULT_EMBEDDING_MODEL

        if not content:
            raise EmptyContentError()

        mimetype = detect_mimetype(content, filename, declared_type)

        part = self._to_embeddable(content, mimetype)

        embeddings = await self.embedding_service.embed(part, model)

        # content-addressed identity: same bytes -> same ids -> re-ingestion
        # overwrites existing points instead of duplicating them
        document_id = hashlib.sha256(content).hexdigest()

        # point identity is scoped by space so the same content can exist in
        # a space and the general store without overwriting each other
        identity = document_id if space_id is None else f"{space_id}/{document_id}"

        records = [
            VectorRecord(
                id=uuid.uuid5(POINT_NAMESPACE, f"{identity}:{index}"),
                vector=vector,
                payload=DocumentPayload(
                    document_id=document_id,
                    filename=filename,
                    mimetype=mimetype,
                    chunk_index=index,
                    model=model,
                    space_id=space_id,
                ),
            )
            for index, vector in enumerate(embeddings)
        ]

        await self.vector_store.upsert(records)

        return IngestionResult(
            document_id=document_id,
            mimetype=mimetype,
            chunks=len(records),
            space_id=space_id,
        )

    def _to_embeddable(self, content: bytes, mimetype: str) -> str | types.Part:
        if mimetype.startswith("text/") or mimetype in TEXT_MIMETYPES:
            text = content.decode("utf-8", errors="replace")
            # Gemini rejects empty parts with an opaque 400; whitespace-only
            # text has nothing to embed either
            if not text.strip():
                raise EmptyContentError()
            return text

        if mimetype in MULTIMODAL_MIMETYPES:
            if mimetype == "application/pdf":
                validate_pdf(content, MAX_PDF_PAGES)
            return types.Part.from_bytes(data=content, mime_type=mimetype)

        raise UnsupportedMimetypeError(mimetype)
