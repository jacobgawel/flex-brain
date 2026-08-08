from .base import ClientManager
from .gemini_client import GeminiManager, get_gemini_client
from .qdrant_client import QdrantManager, get_qdrant_client

_managers: list[ClientManager] = [GeminiManager(), QdrantManager()]


async def initialize_all() -> None:
    for manager in _managers:
        await manager.initialize()


async def close_all() -> None:
    for manager in _managers:
        await manager.close()


__all__ = ["get_gemini_client", "get_qdrant_client"]
