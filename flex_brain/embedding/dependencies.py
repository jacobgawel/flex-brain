from typing import Annotated

from fastapi import Depends

from flex_brain.clients.gemini_client import GeminiClientDep

from .service import EmbeddingService


def get_embedding_service(gemini_client: GeminiClientDep) -> EmbeddingService:
    return EmbeddingService(gemini_client=gemini_client)


EmbeddingServiceDep = Annotated[EmbeddingService, Depends(get_embedding_service)]
