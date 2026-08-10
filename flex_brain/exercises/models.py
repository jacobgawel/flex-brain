import uuid

from pydantic import BaseModel, Field

# bundle input: the raw RepDB exercises.json. only the fields the feature
# uses are declared — pydantic ignores the rest (locales, images, relations,
# met, ...) by default, so a bundle update adding fields never breaks parsing


class BundleMuscle(BaseModel):
    name_en: str
    name_scientific: str | None = None


class BundleEquipment(BaseModel):
    name_en: str


class BundleExercise(BaseModel):
    id: str = Field(min_length=1, description="the exercise slug")
    name_en: str
    description_en: str | None = None
    category: str
    force_type: str | None = None
    mechanic: str | None = None
    difficulty: str | None = None
    equipment: str | None = None
    body_part: str | None = None
    is_unilateral: bool = False
    is_bodyweight: bool = False
    is_placeholder: bool = False
    goals: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)


class ExerciseBundle(BaseModel):
    muscles: dict[str, BundleMuscle]
    equipment: dict[str, BundleEquipment]
    exercises: list[BundleExercise]


# vector-store domain models


class ExercisePayload(BaseModel):
    slug: str
    category: str
    equipment: str | None
    difficulty: str | None
    body_part: str | None
    primary_muscles: list[str]
    secondary_muscles: list[str]
    goals: list[str]
    is_bodyweight: bool
    is_unilateral: bool
    model: str


class ExerciseRecord(BaseModel):
    id: uuid.UUID
    vector: list[float]
    payload: ExercisePayload


class ExerciseSearchResult(BaseModel):
    score: float
    payload: ExercisePayload


# api models


class ExerciseIndexResponse(BaseModel):
    model: str
    exercises_indexed: int
    placeholders_skipped: int
    deleted: int


class ExerciseSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=10, ge=1, le=100)
    model: str | None = None
    category: str | None = None
    equipment: str | None = None
    difficulty: str | None = None
    body_part: str | None = None
    muscle: str | None = Field(
        default=None, description="matches primary or secondary muscles"
    )
    goal: str | None = None
    is_bodyweight: bool | None = None
    is_unilateral: bool | None = None


class ExerciseSearchHit(BaseModel):
    slug: str
    score: float
    category: str
    equipment: str | None
    difficulty: str | None
    body_part: str | None
    primary_muscles: list[str]
    secondary_muscles: list[str]
    goals: list[str]
    is_bodyweight: bool
    is_unilateral: bool


class ExerciseSearchResponse(BaseModel):
    model: str
    hits: list[ExerciseSearchHit]
