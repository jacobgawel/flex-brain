import uuid

from qdrant_client import AsyncQdrantClient, models

from flex_brain.constants import EMBEDDING_DIMENSIONS
from flex_brain.vector_store.models import DocumentPayload, SearchResult, VectorRecord


class VectorStoreService:
    """Storage and retrieval of document embeddings in a Qdrant collection.

    Pure persistence layer: takes ready-made vectors in and returns vectors
    with payloads out. Knows nothing about embedding generation or file
    handling, and callers never see qdrant types — the boundary is the
    domain models (VectorRecord, SearchResult).
    """

    def __init__(self, qdrant_client: AsyncQdrantClient, collection_name: str):
        self.qdrant_client = qdrant_client
        self.collection_name = collection_name

    async def ensure_collection(self) -> None:
        """create the collection if it does not exist yet; idempotent"""

        if not await self.qdrant_client.collection_exists(self.collection_name):
            await self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=EMBEDDING_DIMENSIONS,
                    distance=models.Distance.COSINE,
                ),
            )

        # keyword index speeds up document_id filters (delete_document, search);
        # a no-op when the index already exists
        await self.qdrant_client.create_payload_index(
            collection_name=self.collection_name,
            field_name="document_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

        await self.qdrant_client.create_payload_index(
            collection_name=self.collection_name,
            field_name="space_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    async def upsert(self, records: list[VectorRecord]) -> None:
        """insert points, overwriting any existing point with the same id"""
        if not records:
            return

        await self.qdrant_client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=str(record.id),
                    vector=record.vector,
                    payload=record.payload.model_dump(),
                )
                for record in records
            ],
        )

    async def search(
        self,
        vector: list[float],
        limit: int = 10,
        document_id: str | None = None,
        space_id: str | None = None,
    ) -> list[SearchResult]:
        """Nearest-neighbour search, optionally restricted to one document.

        Spaces partition the collection: with a space_id only that space is
        searched; without one only the general store (points with no space)
        is searched. Spaced points never appear in unscoped searches.
        """

        response = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            query_filter=self._search_filter(document_id, space_id),
            with_payload=True,
        )

        return [
            SearchResult(
                id=uuid.UUID(str(point.id)),
                score=point.score,
                payload=DocumentPayload.model_validate(point.payload),
            )
            for point in response.points
        ]

    @staticmethod
    def _search_filter(document_id: str | None, space_id: str | None) -> models.Filter:
        conditions: list[models.Condition] = []

        if document_id is not None:
            conditions.append(
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            )

        if space_id is not None:
            conditions.append(
                models.FieldCondition(
                    key="space_id",
                    match=models.MatchValue(value=space_id),
                )
            )
        else:
            # IsEmpty matches points where space_id is missing or null,
            # keeping spaced points out of general-store searches
            conditions.append(
                models.IsEmptyCondition(is_empty=models.PayloadField(key="space_id"))
            )

        return models.Filter(must=conditions)

    @staticmethod
    def _document_filter(document_id: str) -> models.Filter:
        return models.Filter(
            must=[
                models.FieldCondition(
                    key="document_id",
                    match=models.MatchValue(value=document_id),
                )
            ]
        )

    async def delete_document(self, document_id: str) -> int:
        """Delete every chunk of a document by payload filter.

        Returns the number of points that matched (0 if the document
        was never ingested — no exception is raised).
        """

        document_filter = self._document_filter(document_id)

        count = await self.qdrant_client.count(
            collection_name=self.collection_name,
            count_filter=document_filter,
            exact=True,
        )

        if count.count == 0:
            return 0

        await self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(filter=document_filter),
        )

        return count.count
