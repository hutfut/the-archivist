# Backend -- The Archive API

Document management, RAG-powered chat, and semantic search, built with FastAPI, LangGraph, and PostgreSQL + pgvector.

---

## Prerequisites

- Python 3.12+
- PostgreSQL 17 with the [pgvector](https://github.com/pgvector/pgvector) extension
- Docker (only needed for running tests via [testcontainers](https://testcontainers.com/))

---

## Local Development

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Set up the database (assumes Postgres is running)
export DATABASE_URL="postgresql+asyncpg://notebooklm:notebooklm@localhost:5432/notebooklm"
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

The API is available at [http://localhost:8000](http://localhost:8000), with interactive OpenAPI docs at [http://localhost:8000/docs](http://localhost:8000/docs).

---

## Environment Variables

All configuration is in [`app/config.py`](app/config.py). Every field reads from an environment variable with a sensible default.

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://notebooklm:notebooklm@localhost:5432/notebooklm` | Async SQLAlchemy connection string |
| `UPLOAD_DIR` | `data/uploads` | Filesystem path for stored document files |
| `MAX_UPLOAD_BYTES` | `52428800` (50 MB) | Maximum upload file size |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model for embeddings |
| `LLM_PROVIDER` | `mock` | LLM backend: `mock`, `ollama`, or `anthropic` |
| `OLLAMA_MODEL` | `llama3` | Model name when using Ollama |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `ANTHROPIC_API_KEY` | *(empty)* | API key for Anthropic Claude |
| `ANTHROPIC_MODEL` | `claude-sonnet-4-20250514` | Model name when using Anthropic |
| `RETRIEVAL_MODE` | `hybrid` | Search mode: `vector`, `keyword`, or `hybrid` |
| `RETRIEVAL_TOP_K` | `5` | Number of chunks returned to the LLM |
| `RETRIEVAL_CANDIDATE_K` | `20` | Candidate pool size before re-ranking |
| `SIMILARITY_THRESHOLD` | `0.3` | Minimum similarity score for retrieval |
| `MAX_HISTORY_MESSAGES` | `50` | Conversation history window sent to the LLM |
| `LOG_LEVEL` | `INFO` | Python logging level |

---

## Running Tests

```bash
pytest
```

Tests use [testcontainers](https://testcontainers.com/) to spin up an ephemeral PostgreSQL instance with pgvector -- Docker must be running. To use an existing database instead, set `DATABASE_URL` before running pytest.

---

## API Overview

All endpoints are prefixed with `/api`.

### Health

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/health` | Database connectivity check |

### Documents

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents` | Upload a document (PDF, TXT, MD) |
| `GET` | `/api/documents` | List documents (paginated) |
| `DELETE` | `/api/documents/{id}` | Delete a document and its chunks |
| `GET` | `/api/documents/{id}/content` | Get full extracted text |
| `GET` | `/api/documents/{id}/related` | Find related documents by embedding similarity |

### Search

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/search?q=...` | Semantic search across document chunks |

### Conversations

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/conversations` | Create a new conversation |
| `GET` | `/api/conversations` | List conversations (paginated) |
| `GET` | `/api/conversations/{id}` | Get conversation with message history |
| `DELETE` | `/api/conversations/{id}` | Delete a conversation |
| `POST` | `/api/conversations/{id}/messages` | Send a message (synchronous response) |
| `POST` | `/api/conversations/{id}/messages/stream` | Send a message (SSE streaming response) |

