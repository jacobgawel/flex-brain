# flex-brain

A FastAPI service that ingests documents, embeds them with Google's `gemini-embedding-2` model, and stores the vectors in [Qdrant](https://qdrant.tech/) for semantic search.

## How it works

1. **Ingest** — upload a file; its mimetype is detected with [Magika](https://github.com/google/magika), the content is embedded via the Gemini API, and the vectors are upserted into Qdrant. Document identity is content-addressed (SHA-256 of the bytes), so re-ingesting the same file overwrites its existing points instead of duplicating them.
2. **Search** — send a text query; it is embedded with the same model and matched against stored vectors, optionally scoped to a single document.

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
# 1. Start Qdrant (and Postgres) locally
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

## API

### `GET /health`

Liveness check. Returns `{"status": "ok"}`.

### `POST /ingestion`

Multipart form upload.

| Field | Type | Description |
| --- | --- | --- |
| `file` | file | The document to ingest |
| `model` | string (optional) | Embedding model, defaults to `gemini-embedding-2` |

```sh
curl -X POST http://127.0.0.1:8000/ingestion -F "file=@document.pdf"
```

Returns the `document_id`, detected mimetype, and number of chunks stored. Errors: `415` for unsupported mimetypes, `400` for invalid PDFs, `413` for PDFs over the page limit.

### `POST /search`

JSON body.

| Field | Type | Description |
| --- | --- | --- |
| `query` | string | Search text |
| `limit` | int (optional) | Max hits, 1–100, defaults to 10 |
| `model` | string (optional) | Embedding model, must match the one used at ingestion |
| `document_id` | string (optional) | Restrict the search to one ingested document |

```sh
curl -X POST http://127.0.0.1:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "what is the refund policy?", "limit": 5}'
```

Returns scored hits with the source document's id, filename, mimetype, and chunk index.

A [Bruno](https://www.usebruno.com/) collection with ready-made requests is available in [bruno/](bruno/).

## Project structure

```
flex_brain/
├── main.py           # FastAPI app, lifespan, router wiring
├── config.py         # pydantic-settings configuration
├── clients/          # Gemini and Qdrant client lifecycle
├── constants/        # embedding model and vector store constants
├── embedding/        # embedding generation via Gemini
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
