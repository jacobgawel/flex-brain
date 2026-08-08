from typing import Annotated

from fastapi import Depends
from qdrant_client import AsyncQdrantClient

from flex_brain.clients.base import ClientManager
from flex_brain.config import config


class QdrantManager(ClientManager[AsyncQdrantClient]):
    """Singleton manager for the async qdrant client"""

    async def _create_client(self) -> AsyncQdrantClient:
        return AsyncQdrantClient(
            url=config.qdrant_url,
            # empty setting means no auth (local docker-compose); passing ""
            # would send an api-key header and trigger insecure-connection warnings
            api_key=config.qdrant_api_key.get_secret_value() or None,
        )

    async def _close_client(self) -> None:
        await self.client.close()


_qdrant_singleton = QdrantManager()


def get_qdrant_client() -> AsyncQdrantClient:
    return _qdrant_singleton.client


QdrantClientDep = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]
