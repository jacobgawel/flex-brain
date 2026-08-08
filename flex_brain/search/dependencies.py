from typing import Annotated

from fastapi import Depends

from flex_brain.embedding import EmbeddingServiceDep
from flex_brain.vector_store import VectorStoreServiceDep

from .service import SearchService


def get_search_service(
    embedding_service: EmbeddingServiceDep, vector_store: VectorStoreServiceDep
) -> SearchService:
    return SearchService(embedding_service=embedding_service, vector_store=vector_store)


SearchServiceDep = Annotated[SearchService, Depends(get_search_service)]
