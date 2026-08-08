from flex_brain.constants import DEFAULT_EMBEDDING_MODEL
from flex_brain.embedding import EmbeddingService
from flex_brain.vector_store import VectorStoreService
from flex_brain.vector_store.models import SearchResult


class SearchService:
    """semantic search over ingested documents"""

    def __init__(
        self, embedding_service: EmbeddingService, vector_store: VectorStoreService
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def search(
        self,
        query: str,
        limit: int = 10,
        model: str | None = None,
        document_id: str | None = None,
    ) -> list[SearchResult]:
        if model is None:
            model = DEFAULT_EMBEDDING_MODEL

        vectors = await self.embedding_service.embed(query, model)

        return await self.vector_store.search(
            vectors[0], limit=limit, document_id=document_id
        )
