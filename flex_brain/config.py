from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment variables and `.env`.

    Field names map to env vars case-insensitively (e.g. `gemini_api_key`
    is read from GEMINI_API_KEY). Values from the environment take
    precedence over `.env`.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = Field(
        default="flex-brain",
        description="Application name, shown in the OpenAPI docs and logs",
    )
    debug: bool = Field(
        default=False,
        description="Enable debug behaviour (verbose logging, detailed errors)",
    )

    host: str = Field(
        default="127.0.0.1",
        description=(
            "Host configuration, for local development it should be configured"
            "to localhost (127.0.0.1) to avoid resolving delays."
        ),
    )

    port: int = Field(default=8000, description="Port configuration")

    # GEMINI CONFIGURATION
    gemini_api_key: SecretStr = Field(
        ...,
        description=(
            "Google AI Studio API key used for embedding generation; "
            "required — the app fails at startup without it"
        ),
    )

    # QDRANT CONFIGURATION
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Base URL of the Qdrant instance (docker-compose default)",
    )
    qdrant_collection: str = Field(
        default="documents",
        description="Qdrant collection that stores document embeddings",
    )
    qdrant_exercise_collection: str = Field(
        default="exercises",
        description="Qdrant collection that stores exercise embeddings",
    )
    qdrant_api_key: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "API key sent with every Qdrant request; required for Qdrant Cloud "
            "or a self-hosted instance with auth enabled, leave empty for the "
            "unauthenticated local docker-compose setup"
        ),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue] -- fields populated from env


config = get_settings()
