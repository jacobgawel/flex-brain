import uuid

# fixed namespace for deterministic point ids: uuid5(POINT_NAMESPACE,
# f"{document_id}:{chunk_index}"). never change this value once data has
# been ingested — every derived id changes with it, so re-ingestion would
# duplicate existing points instead of overwriting them
POINT_NAMESPACE = uuid.UUID("79780256-a930-4e50-a703-a31424d86f66")

# fixed namespace for deterministic exercise point ids:
# uuid5(EXERCISE_POINT_NAMESPACE, slug) — one point per exercise, so
# re-indexing a bundle overwrites each exercise in place. distinct from
# POINT_NAMESPACE so document and exercise ids can never collide. never
# change this value once exercises have been indexed — every derived id
# changes with it, so re-indexing would duplicate existing points
# instead of overwriting them
EXERCISE_POINT_NAMESPACE = uuid.UUID("9c4a8e3d-51f6-4b2a-8d07-63e19a5cfb42")
