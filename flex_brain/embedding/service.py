from google import genai
from google.genai import types

from flex_brain.constants import EMBEDDING_DIMENSIONS


class EmbeddingService:
    """Embedding generation via the Gemini API.

    Shared by ingestion (embedding document content) and search (embedding
    the query) so both sides are guaranteed to use the same model settings
    and output dimensionality — vectors are only comparable within one model.
    """

    def __init__(self, gemini_client: genai.Client):
        self.gemini_client = gemini_client

    async def embed(self, content: str | types.Part, model: str) -> list[list[float]]:
        config: types.EmbedContentConfigDict = {
            "output_dimensionality": EMBEDDING_DIMENSIONS
        }

        result = await self.gemini_client.aio.models.embed_content(
            model=model, contents=[content], config=config
        )

        return [embedding.values or [] for embedding in result.embeddings or []]
