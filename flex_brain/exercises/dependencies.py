from typing import Annotated

from fastapi import Depends

from flex_brain.clients.qdrant_client import QdrantClientDep
from flex_brain.config import get_settings
from flex_brain.embedding import EmbeddingServiceDep

from .service import ExerciseService
from .vector_store import ExerciseVectorStoreService


def get_exercise_vector_store(
    qdrant_client: QdrantClientDep,
) -> ExerciseVectorStoreService:
    return ExerciseVectorStoreService(
        qdrant_client=qdrant_client,
        collection_name=get_settings().qdrant_exercise_collection,
    )


ExerciseVectorStoreDep = Annotated[
    ExerciseVectorStoreService, Depends(get_exercise_vector_store)
]


def get_exercise_service(
    embedding_service: EmbeddingServiceDep, vector_store: ExerciseVectorStoreDep
) -> ExerciseService:
    return ExerciseService(
        embedding_service=embedding_service, vector_store=vector_store
    )


ExerciseServiceDep = Annotated[ExerciseService, Depends(get_exercise_service)]
