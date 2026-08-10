from qdrant_client import AsyncQdrantClient, models

from flex_brain.constants import EMBEDDING_DIMENSIONS
from flex_brain.exercises.models import (
    ExercisePayload,
    ExerciseRecord,
    ExerciseSearchResult,
)

# every filterable payload field, with the index type that makes its
# filter condition hit an index instead of a full scan
_KEYWORD_FIELDS = (
    "slug",
    "category",
    "equipment",
    "difficulty",
    "body_part",
    "primary_muscles",
    "secondary_muscles",
    "goals",
)
_BOOL_FIELDS = ("is_bodyweight", "is_unilateral")


class ExerciseVectorStoreService:
    """Storage and retrieval of exercise embeddings in their own collection.

    Deliberately separate from the general document store: exercises are a
    catalog with one point per slug and a structured, filterable payload,
    not chunked documents — sharing a collection would force both features
    onto one payload schema and one identity scheme.
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

        # a no-op when the index already exists; list-valued keyword fields
        # (muscles, goals) index every element, which is what makes a
        # MatchValue condition against them behave as "contains"
        for field in _KEYWORD_FIELDS:
            await self.qdrant_client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.KEYWORD,
            )

        for field in _BOOL_FIELDS:
            await self.qdrant_client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field,
                field_schema=models.PayloadSchemaType.BOOL,
            )

    async def upsert(self, records: list[ExerciseRecord]) -> None:
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

    async def delete_missing(self, slugs: list[str]) -> int:
        """Delete every point whose slug is not in the given set.

        Run after an upsert so a bundle re-index prunes exercises the new
        bundle no longer contains, with no window where a still-valid
        exercise is absent. Returns the number of points deleted.
        """

        # MatchExcept has no python-name population, so the "except" alias
        # must be passed via dict expansion
        stale_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="slug",
                    match=models.MatchExcept(**{"except": slugs}),
                )
            ]
        )

        count = await self.qdrant_client.count(
            collection_name=self.collection_name,
            count_filter=stale_filter,
            exact=True,
        )

        if count.count == 0:
            return 0

        await self.qdrant_client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(filter=stale_filter),
        )

        return count.count

    async def search(
        self,
        vector: list[float],
        limit: int = 10,
        category: str | None = None,
        equipment: str | None = None,
        difficulty: str | None = None,
        body_part: str | None = None,
        muscle: str | None = None,
        goal: str | None = None,
        is_bodyweight: bool | None = None,
        is_unilateral: bool | None = None,
    ) -> list[ExerciseSearchResult]:
        """nearest-neighbour search, restricted by any payload filters given"""

        response = await self.qdrant_client.query_points(
            collection_name=self.collection_name,
            query=vector,
            limit=limit,
            query_filter=self._search_filter(
                category=category,
                equipment=equipment,
                difficulty=difficulty,
                body_part=body_part,
                muscle=muscle,
                goal=goal,
                is_bodyweight=is_bodyweight,
                is_unilateral=is_unilateral,
            ),
            with_payload=True,
        )

        return [
            ExerciseSearchResult(
                score=point.score,
                payload=ExercisePayload.model_validate(point.payload),
            )
            for point in response.points
        ]

    @staticmethod
    def _search_filter(
        category: str | None,
        equipment: str | None,
        difficulty: str | None,
        body_part: str | None,
        muscle: str | None,
        goal: str | None,
        is_bodyweight: bool | None,
        is_unilateral: bool | None,
    ) -> models.Filter | None:
        must: list[models.Condition] = [
            models.FieldCondition(key=key, match=models.MatchValue(value=value))
            for key, value in (
                ("category", category),
                ("equipment", equipment),
                ("difficulty", difficulty),
                ("body_part", body_part),
                ("goals", goal),
                ("is_bodyweight", is_bodyweight),
                ("is_unilateral", is_unilateral),
            )
            if value is not None
        ]

        # a muscle qualifies whether the exercise targets it or merely
        # assists with it: OR across the two arrays, nested inside the AND
        if muscle is not None:
            must.append(
                models.Filter(
                    should=[
                        models.FieldCondition(
                            key="primary_muscles",
                            match=models.MatchValue(value=muscle),
                        ),
                        models.FieldCondition(
                            key="secondary_muscles",
                            match=models.MatchValue(value=muscle),
                        ),
                    ]
                )
            )

        return models.Filter(must=must) if must else None
