import uuid
from dataclasses import dataclass

from flex_brain.constants import (
    DEFAULT_EMBEDDING_MODEL,
    EXERCISE_POINT_NAMESPACE,
    TASK_TYPE_RETRIEVAL_DOCUMENT,
    TASK_TYPE_RETRIEVAL_QUERY,
)
from flex_brain.embedding import EmbeddingService
from flex_brain.exercises.models import (
    BundleEquipment,
    BundleExercise,
    BundleMuscle,
    ExerciseBundle,
    ExercisePayload,
    ExerciseRecord,
    ExerciseSearchResult,
)
from flex_brain.exercises.vector_store import ExerciseVectorStoreService


class UnknownReferenceError(Exception):
    def __init__(self, kind: str, slug: str, exercise_slug: str):
        self.kind = kind
        self.slug = slug
        self.exercise_slug = exercise_slug
        super().__init__(
            f"exercise '{exercise_slug}' references unknown {kind} '{slug}'"
        )


def _display(slug: str) -> str:
    """ "upper_arms" -> "upper arms\""""
    return slug.replace("_", " ")


def _article(noun: str) -> str:
    return "an" if noun[:1].lower() in "aeiou" else "a"


def _join(names: list[str]) -> str:
    """ "a", "a and b", "a, b and c\""""
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


def compose_embedding_text(
    exercise: BundleExercise,
    muscles: dict[str, BundleMuscle],
    equipment: dict[str, BundleEquipment],
) -> str:
    """Render one exercise as the text that gets embedded.

    Name and synonyms lead because most queries are half-remembered
    exercise names; the attributes follow as sentences built from display
    names, not slugs — "works the rectus abdominis" carries semantic
    signal that "rectus_abdominis" does not. Absent data drops its
    sentence rather than leaving a hole.
    """

    lines: list[str] = []

    title = f"{exercise.name_en}."
    if exercise.synonyms:
        title += f" Also known as: {', '.join(exercise.synonyms)}."
    lines.append(title)

    category = _display(exercise.category)
    sentence = f"{_article(category).capitalize()} {category} exercise"

    movement = " ".join(
        _display(part)
        for part in (exercise.mechanic, exercise.force_type)
        if part is not None
    )
    if movement:
        sentence += f" — {movement} movement"
    if exercise.body_part is not None:
        sentence += f" for the {_display(exercise.body_part)}"

    if exercise.equipment is not None:
        if exercise.equipment not in equipment:
            raise UnknownReferenceError("equipment", exercise.equipment, exercise.id)
        name = equipment[exercise.equipment].name_en.lower()
        sentence += f", using {_article(name)} {name}"
    else:
        sentence += ", using no equipment"
    lines.append(sentence + ".")

    def muscle_names(slugs: list[str]) -> list[str]:
        names: list[str] = []
        for slug in slugs:
            if slug not in muscles:
                raise UnknownReferenceError("muscle", slug, exercise.id)
            muscle = muscles[slug]
            name = muscle.name_en.lower()
            # both vocabularies so "lats" and "latissimus dorsi" queries
            # match alike; skip the parenthetical when they coincide
            scientific = (muscle.name_scientific or "").lower()
            if scientific and scientific != name:
                name += f" ({scientific})"
            names.append(name)
        return names

    if exercise.primary_muscles:
        worked = f"Primarily works the {_join(muscle_names(exercise.primary_muscles))}"
        if exercise.secondary_muscles:
            worked += (
                f"; also works the {_join(muscle_names(exercise.secondary_muscles))}"
            )
        lines.append(worked + ".")

    training = ""
    if exercise.goals:
        goals = _join([_display(goal) for goal in exercise.goals])
        training = f"Suited to {goals} training."
    if exercise.difficulty is not None:
        training += (
            f"{' ' if training else ''}{exercise.difficulty.capitalize()} difficulty."
        )
    if training:
        lines.append(training)

    if exercise.description_en:
        lines.append(exercise.description_en)

    return "\n".join(lines)


@dataclass
class ExerciseIndexResult:
    model: str
    exercises_indexed: int
    placeholders_skipped: int
    deleted: int


class ExerciseService:
    """indexing and semantic search over the exercise catalog"""

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_store: ExerciseVectorStoreService,
    ):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def index(
        self, bundle: ExerciseBundle, model: str | None = None
    ) -> ExerciseIndexResult:
        if model is None:
            model = DEFAULT_EMBEDDING_MODEL

        active = [e for e in bundle.exercises if not e.is_placeholder]

        # compose everything before embedding so a bad reference fails the
        # request before any gemini spend
        texts = [
            compose_embedding_text(e, bundle.muscles, bundle.equipment) for e in active
        ]

        vectors = await self.embedding_service.embed_batch(
            texts, model, task_type=TASK_TYPE_RETRIEVAL_DOCUMENT
        )

        records = [
            ExerciseRecord(
                # one point per exercise, keyed by slug: re-indexing a newer
                # bundle overwrites in place instead of accumulating duplicates
                id=uuid.uuid5(EXERCISE_POINT_NAMESPACE, exercise.id),
                vector=vector,
                payload=ExercisePayload(
                    slug=exercise.id,
                    category=exercise.category,
                    equipment=exercise.equipment,
                    difficulty=exercise.difficulty,
                    body_part=exercise.body_part,
                    primary_muscles=exercise.primary_muscles,
                    secondary_muscles=exercise.secondary_muscles,
                    goals=exercise.goals,
                    is_bodyweight=exercise.is_bodyweight,
                    is_unilateral=exercise.is_unilateral,
                    model=model,
                ),
            )
            for exercise, vector in zip(active, vectors, strict=True)
        ]

        await self.vector_store.upsert(records)
        deleted = await self.vector_store.delete_missing([e.id for e in active])

        return ExerciseIndexResult(
            model=model,
            exercises_indexed=len(records),
            placeholders_skipped=len(bundle.exercises) - len(active),
            deleted=deleted,
        )

    async def search(
        self,
        query: str,
        limit: int = 10,
        model: str | None = None,
        category: str | None = None,
        equipment: str | None = None,
        difficulty: str | None = None,
        body_part: str | None = None,
        muscle: str | None = None,
        goal: str | None = None,
        is_bodyweight: bool | None = None,
        is_unilateral: bool | None = None,
    ) -> list[ExerciseSearchResult]:
        if model is None:
            model = DEFAULT_EMBEDDING_MODEL

        vectors = await self.embedding_service.embed(
            query, model, task_type=TASK_TYPE_RETRIEVAL_QUERY
        )

        return await self.vector_store.search(
            vectors[0],
            limit=limit,
            category=category,
            equipment=equipment,
            difficulty=difficulty,
            body_part=body_part,
            muscle=muscle,
            goal=goal,
            is_bodyweight=is_bodyweight,
            is_unilateral=is_unilateral,
        )
