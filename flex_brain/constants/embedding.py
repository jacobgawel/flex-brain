DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"
EMBEDDING_DIMENSIONS = 3072  # output dimensionality of gemini-embedding-2

# gemini-embedding-2 has no server-side batch: a request with several
# contents returns a single joint embedding, not one per content. bulk
# embedding is therefore one request per text, bounded by this many
# in-flight requests, backing off on 429s (free-tier limits are per-minute)
EMBEDDING_CONCURRENCY = 4
EMBEDDING_MAX_ATTEMPTS = 6
EMBEDDING_BACKOFF_BASE_SECONDS = 2

# asymmetric retrieval pair: documents are embedded with one task type and
# queries with the other, which tunes the vectors for search rather than
# plain similarity — both sides must use the pair or scores degrade
TASK_TYPE_RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
TASK_TYPE_RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
