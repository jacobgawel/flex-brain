from fastapi import APIRouter

from flex_brain.constants import DEFAULT_EMBEDDING_MODEL
from flex_brain.search.dependencies import SearchServiceDep
from flex_brain.search.models import SearchHit, SearchRequest, SearchResponse

router = APIRouter(prefix="/search", tags=["search"])


@router.post("")
async def search(
    request: SearchRequest, search_service: SearchServiceDep
) -> SearchResponse:
    model = request.model or DEFAULT_EMBEDDING_MODEL

    results = await search_service.search(
        query=request.query,
        limit=request.limit,
        model=model,
        document_id=request.document_id,
    )

    return SearchResponse(
        model=model,
        hits=[
            SearchHit(
                id=result.id,
                score=result.score,
                document_id=result.payload.document_id,
                filename=result.payload.filename,
                mimetype=result.payload.mimetype,
                chunk_index=result.payload.chunk_index,
            )
            for result in results
        ],
    )
