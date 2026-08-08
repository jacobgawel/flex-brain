from typing import Annotated

from fastapi import Depends
from google import genai

from flex_brain.clients.base import ClientManager
from flex_brain.config import config


class GeminiManager(ClientManager[genai.Client]):
    """Singleton manager for the gemini genai client"""

    async def _create_client(self) -> genai.Client:
        return genai.Client(api_key=config.gemini_api_key.get_secret_value())

    async def _close_client(self) -> None:
        self.client.close()
        await self.client.aio.aclose()


_gemini_singleton = GeminiManager()


def get_gemini_client() -> genai.Client:
    return _gemini_singleton.client


GeminiClientDep = Annotated[genai.Client, Depends(get_gemini_client)]
