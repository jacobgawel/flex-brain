from contextlib import asynccontextmanager

from fastapi import FastAPI

from flex_brain import exercises, health, ingestion, search
from flex_brain.clients import close_all, initialize_all
from flex_brain.clients.qdrant_client import get_qdrant_client
from flex_brain.config import config
from flex_brain.exercises.vector_store import ExerciseVectorStoreService
from flex_brain.vector_store import VectorStoreService


@asynccontextmanager
async def lifespan(app: FastAPI):
    await initialize_all()

    vector_store = VectorStoreService(
        qdrant_client=get_qdrant_client(),
        collection_name=config.qdrant_collection,
    )
    await vector_store.ensure_collection()

    exercise_store = ExerciseVectorStoreService(
        qdrant_client=get_qdrant_client(),
        collection_name=config.qdrant_exercise_collection,
    )
    await exercise_store.ensure_collection()

    yield

    await close_all()


app = FastAPI(title=config.app_name, lifespan=lifespan)

app.include_router(health.router)
app.include_router(ingestion.router)
app.include_router(search.router)
app.include_router(exercises.router)


def main() -> None:
    import uvicorn

    # The reason for 127.0.0.1 is to stop the requests from being slow
    uvicorn.run("flex_brain.main:app", host=config.host, port=config.port, reload=True)
