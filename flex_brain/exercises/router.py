from fastapi import APIRouter, HTTPException, status

from flex_brain.constants import DEFAULT_EMBEDDING_MODEL
from flex_brain.exercises.dependencies import ExerciseServiceDep
from flex_brain.exercises.models import (
    ExerciseBundle,
    ExerciseIndexResponse,
    ExerciseSearchHit,
    ExerciseSearchRequest,
    ExerciseSearchResponse,
)
from flex_brain.exercises.service import UnknownReferenceError

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.put("")
async def index_exercises(
    bundle: ExerciseBundle, exercise_service: ExerciseServiceDep
) -> ExerciseIndexResponse:
    try:
        result = await exercise_service.index(bundle)
    except UnknownReferenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    return ExerciseIndexResponse(
        model=result.model,
        exercises_indexed=result.exercises_indexed,
        placeholders_skipped=result.placeholders_skipped,
        deleted=result.deleted,
    )


@router.post("/search")
async def search_exercises(
    request: ExerciseSearchRequest, exercise_service: ExerciseServiceDep
) -> ExerciseSearchResponse:
    model = request.model or DEFAULT_EMBEDDING_MODEL

    results = await exercise_service.search(
        query=request.query,
        limit=request.limit,
        model=model,
        category=request.category,
        equipment=request.equipment,
        difficulty=request.difficulty,
        body_part=request.body_part,
        muscle=request.muscle,
        goal=request.goal,
        is_bodyweight=request.is_bodyweight,
        is_unilateral=request.is_unilateral,
    )

    return ExerciseSearchResponse(
        model=model,
        hits=[
            ExerciseSearchHit(
                slug=result.payload.slug,
                score=result.score,
                category=result.payload.category,
                equipment=result.payload.equipment,
                difficulty=result.payload.difficulty,
                body_part=result.payload.body_part,
                primary_muscles=result.payload.primary_muscles,
                secondary_muscles=result.payload.secondary_muscles,
                goals=result.payload.goals,
                is_bodyweight=result.payload.is_bodyweight,
                is_unilateral=result.payload.is_unilateral,
            )
            for result in results
        ],
    )
