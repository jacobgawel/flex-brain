# flex-brain

A FastAPI service that ingests documents, embeds them with Google's `gemini-embedding-2` model, and stores the vectors in [Qdrant](https://qdrant.tech/) for semantic search.

## How it works

1. **Ingest** — upload a file; its mimetype is detected with [Magika](https://github.com/google/magika), the content is embedded via the Gemini API, and the vectors are upserted into Qdrant. Document identity is content-addressed (SHA-256 of the bytes), so re-ingesting the same file overwrites its existing points instead of duplicating them.
2. **Search** — send a text query; it is embedded with the same model and matched against stored vectors, optionally scoped to a single document.

### Spaces

Documents can be ingested into a **space** (an arbitrary `space_id` string), which partitions the collection. Searches with a `space_id` only see that space; searches without one only see documents ingested without a space (the general store) — spaced documents never leak into unscoped searches. Point identity is scoped per space, so the same file can live in a space and the general store without overwriting each other.

### Supported file types

- Text: any `text/*`, plus JSON, XML, and YAML
- Images: PNG, JPEG
- Audio: MP3, WAV
- PDF: up to 6 pages

Per-request Gemini model limits apply (6 images, 180s audio, 8192 tokens total).

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- Docker (for Qdrant)
- A [Google AI Studio](https://aistudio.google.com/) API key

## Getting started

```sh
# 1. Start Qdrant locally
docker compose up -d

# 2. Configure environment
cp .env.example .env   # then set GEMINI_API_KEY

# 3. Install dependencies and run
uv sync
uv run flex-brain
```

The API is served at `http://127.0.0.1:8000` with interactive docs at `/docs`.

## Configuration

Settings are loaded from environment variables or `.env` (see [config.py](flex_brain/config.py)):

| Variable | Default | Description |
| --- | --- | --- |
| `GEMINI_API_KEY` | — (required) | Google AI Studio API key used for embeddings |
| `QDRANT_URL` | `http://localhost:6333` | Base URL of the Qdrant instance |
| `QDRANT_COLLECTION` | `documents` | Collection that stores document embeddings |
| `QDRANT_API_KEY` | empty | Only needed for Qdrant Cloud or auth-enabled instances |
| `QDRANT_EXERCISE_COLLECTION` | `exercises` | Collection that stores exercise embeddings |

## API

### `GET /health`

Liveness check. Returns `{"status": "ok"}`.

### `POST /ingestion`

Multipart form upload.

| Field | Type | Description |
| --- | --- | --- |
| `file` | file | The document to ingest |
| `model` | string (optional) | Embedding model, defaults to `gemini-embedding-2` |
| `space_id` | string (optional) | Space to ingest into; omit for the general store |

```sh
curl -X POST http://127.0.0.1:8000/ingestion -F "file=@document.pdf"
```

Returns the `document_id`, detected mimetype, number of chunks stored, and the `space_id` (if any). Errors: `415` for unsupported mimetypes, `400` for invalid PDFs, `413` for PDFs over the page limit.

### `POST /search`

JSON body.

| Field | Type | Description |
| --- | --- | --- |
| `query` | string | Search text |
| `limit` | int (optional) | Max hits, 1–100, defaults to 10 |
| `model` | string (optional) | Embedding model, must match the one used at ingestion |
| `document_id` | string (optional) | Restrict the search to one ingested document |
| `space_id` | string (optional) | Search only this space; when omitted, only the general store is searched |

```sh
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the refund policy?", "limit": 5}'
```

Returns scored hits with the source document's id, filename, mimetype, chunk index, and space.

### `PUT /exercises`

JSON body: a raw RepDB bundle `exercises.json`, posted verbatim. Each non-placeholder exercise is rendered to a search text (name + synonyms first, then attribute sentences using display names, then the description), embedded with the `RETRIEVAL_DOCUMENT` task type, and upserted into the dedicated exercises collection — separate from the document store — with a structured payload for filtering. Idempotent: point ids derive from the exercise slug, so re-indexing overwrites in place, and exercises missing from the bundle are deleted afterwards.

```sh
curl -X PUT http://127.0.0.1:8000/exercises \
  -H "Content-Type: application/json" \
  --data-binary @exercises.json
```

Returns the embedding `model` and counts: `exercises_indexed`, `placeholders_skipped`, `deleted`. Errors: `400` when an exercise references a muscle or equipment slug missing from the bundle's lookup dicts.

### `POST /exercises/search`

JSON body. The query is embedded with the `RETRIEVAL_QUERY` task type — the counterpart of the document embeddings — and matched against the exercises collection.

| Field | Type | Description |
| --- | --- | --- |
| `query` | string | Search text |
| `limit` | int (optional) | Max hits, 1–100, defaults to 10 |
| `model` | string (optional) | Embedding model, must match the one used at indexing |
| `category` | string (optional) | Filter, e.g. `strength` |
| `equipment` | string (optional) | Filter by equipment slug, e.g. `barbell` |
| `difficulty` | string (optional) | Filter: `beginner` / `intermediate` / `advanced` |
| `body_part` | string (optional) | Filter, e.g. `core`, `upper_arms` |
| `muscle` | string (optional) | Filter; matches primary **or** secondary muscles |
| `goal` | string (optional) | Filter, e.g. `hypertrophy` |
| `is_bodyweight` | bool (optional) | Filter |
| `is_unilateral` | bool (optional) | Filter |

```sh
curl -X POST http://127.0.0.1:8000/exercises/search \
  -H "Content-Type: application/json" \
  -d '{"query": "easier alternative to a lunge", "limit": 5, "is_bodyweight": true}'
```

Returns scored hits carrying each exercise's `slug` (resolve against the flex-api catalog for display data) and its payload fields.

A [Bruno](https://www.usebruno.com/) collection with ready-made requests is available in [bruno/](bruno/).

## Project structure

```
flex_brain/
├── main.py           # FastAPI app, lifespan, router wiring
├── config.py         # pydantic-settings configuration
├── clients/          # Gemini and Qdrant client lifecycle
├── constants/        # embedding model and vector store constants
├── embedding/        # embedding generation via Gemini
├── exercises/        # PUT /exercises, POST /exercises/search — exercise catalog
├── health/           # GET /health
├── ingestion/        # POST /ingestion — mimetype detection, PDF validation
├── search/           # POST /search — semantic search over stored vectors
└── vector_store/     # Qdrant collection management and upserts
```

## Development

```sh
uv run ruff check .    # lint
uv run ruff format .   # format
```
