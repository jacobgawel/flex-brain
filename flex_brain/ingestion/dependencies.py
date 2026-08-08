from typing import Annotated

from fastapi import Depends

from flex_brain.embedding import EmbeddingServiceDep
from flex_brain.vector_store import VectorStoreServiceDep

from .service import IngestionService


def get_ingestion_service(
    embedding_service: EmbeddingServiceDep, vector_store: VectorStoreServiceDep
) -> IngestionService:
    return IngestionService(
        embedding_service=embedding_service, vector_store=vector_store
    )


IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
