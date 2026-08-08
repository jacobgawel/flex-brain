from typing import Annotated

from fastapi import Depends

from flex_brain.clients.qdrant_client import QdrantClientDep
from flex_brain.config import get_settings

from .service import VectorStoreService


def get_vector_store_service(qdrant_client: QdrantClientDep) -> VectorStoreService:
    return VectorStoreService(
        qdrant_client=qdrant_client,
        collection_name=get_settings().qdrant_collection,
    )


VectorStoreServiceDep = Annotated[VectorStoreService, Depends(get_vector_store_service)]
