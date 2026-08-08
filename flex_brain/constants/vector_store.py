import uuid

# fixed namespace for deterministic point ids: uuid5(POINT_NAMESPACE,
# f"{document_id}:{chunk_index}"). never change this value once data has
# been ingested — every derived id changes with it, so re-ingestion would
# duplicate existing points instead of overwriting them
POINT_NAMESPACE = uuid.UUID("79780256-a930-4e50-a703-a31424d86f66")
