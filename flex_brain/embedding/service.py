import asyncio

from google import genai
from google.genai import errors, types

from flex_brain.constants import (
    EMBEDDING_BACKOFF_BASE_SECONDS,
    EMBEDDING_CONCURRENCY,
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MAX_ATTEMPTS,
)


class EmbeddingService:
    """Embedding generation via the Gemini API.

    Shared by ingestion (embedding document content) and search (embedding
    the query) so both sides are guaranteed to use the same model settings
    and output dimensionality — vectors are only comparable within one model.
    """

    def __init__(self, gemini_client: genai.Client):
        self.gemini_client = gemini_client

    async def embed(
        self,
        content: str | types.Part,
        model: str,
        task_type: str | None = None,
    ) -> list[list[float]]:
        result = await self.gemini_client.aio.models.embed_content(
            model=model, contents=[content], config=self._config(task_type)
        )

        return [embedding.values or [] for embedding in result.embeddings or []]

    async def embed_batch(
        self,
        contents: list[str],
        model: str,
        task_type: str | None = None,
        concurrency: int = EMBEDDING_CONCURRENCY,
    ) -> list[list[float]]:
        """Embed many texts, one request each, order preserved.

        gemini-embedding-2 offers no server-side batch — a request with
        several contents yields a single joint embedding — so bulk work is
        per-text requests behind a semaphore. Free-tier quotas are
        per-minute; a 429 backs off exponentially while still holding the
        semaphore slot, which throttles the whole run rather than letting
        the remaining requests pile into the same exhausted window.
        """

        config = self._config(task_type)
        semaphore = asyncio.Semaphore(concurrency)

        async def embed_one(text: str) -> list[float]:
            async with semaphore:
                for attempt in range(EMBEDDING_MAX_ATTEMPTS):
                    try:
                        result = await self.gemini_client.aio.models.embed_content(
                            model=model, contents=[text], config=config
                        )
                    except errors.ClientError as exc:
                        exhausted = attempt == EMBEDDING_MAX_ATTEMPTS - 1
                        if exc.code != 429 or exhausted:
                            raise
                        await asyncio.sleep(EMBEDDING_BACKOFF_BASE_SECONDS * 2**attempt)
                        continue

                    embeddings = result.embeddings or []
                    return embeddings[0].values or [] if embeddings else []

                raise RuntimeError("unreachable")  # loop always returns or raises

        return list(await asyncio.gather(*(embed_one(text) for text in contents)))

    @staticmethod
    def _config(task_type: str | None) -> types.EmbedContentConfigDict:
        config: types.EmbedContentConfigDict = {
            "output_dimensionality": EMBEDDING_DIMENSIONS
        }

        # omitted entirely when unset so existing callers' requests are
        # unchanged; when set it must be the matching half of a retrieval
        # pair (documents vs queries)
        if task_type is not None:
            config["task_type"] = task_type

        return config
