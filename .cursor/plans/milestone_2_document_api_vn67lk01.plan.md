---
name: ""
overview: ""
todos: []
isProject: false
---

## Milestone 2: Document Management API (Completed)

**Goal**: Full document CRUD over HTTP, persisted to PostgreSQL via SQLAlchemy (metadata) + filesystem (raw files).

### Pre-implementation: ADR 0002

Wrote `.docs/adr/0002-data-storage-strategy.md` covering:

- **PostgreSQL + pgvector** for structured metadata and vector embeddings (replacing the original plan's SQLite + ChromaDB)
- **SQLAlchemy 2.0 async** with `asyncpg` driver -- production-like ORM patterns
- **Filesystem** for raw uploaded files at `data/uploads/{document_id}/{filename}`
- **Alembic** for migrations (runs on container startup via entrypoint)
- Tests use SQLite via `aiosqlite` + `Base.metadata.create_all()` for speed/isolation

### Docker Infrastructure

- `docker-compose.yml` -- full stack: PostgreSQL (pgvector/pgvector:pg17), backend, frontend
- `backend/Dockerfile` + `backend/entrypoint.sh` -- runs `alembic upgrade head` before uvicorn
- `frontend/Dockerfile` + `frontend/nginx.conf` -- multi-stage build, nginx proxies `/api` to backend

### Data Model

SQLAlchemy model (`backend/app/db/models.py`): `Document` with id (UUID string PK), filename, content_type, file_size, chunk_count (default 0), created_at.

Alembic migration `0001_create_documents_table.py` mirrors the model.

Pydantic schemas (`backend/app/models/document.py`): `DocumentResponse` (with `from_attributes`), `DocumentListResponse`.

### New Files (15)

- `docker-compose.yml`, `backend/Dockerfile`, `backend/entrypoint.sh`, `frontend/Dockerfile`, `frontend/nginx.conf`
- `backend/app/config.py` -- `Settings` dataclass (DATABASE_URL, UPLOAD_DIR, ALLOWED_EXTENSIONS from env vars), `get_settings()` dependency
- `backend/app/db/models.py`, `backend/app/db/session.py` -- SQLAlchemy Base/Document model, init_db/close_db/get_session
- `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/script.py.mako`, `backend/alembic/versions/0001_create_documents_table.py`
- `backend/app/models/document.py` -- Pydantic schemas
- `backend/app/services/document_service.py` -- save, list, get, delete operations
- `backend/app/api/documents.py` -- route handlers

### Modified Files (4)

- `backend/app/main.py` -- lifespan (init_db + upload dir), documents router
- `backend/pyproject.toml` -- added sqlalchemy[asyncio], asyncpg, alembic; aiosqlite as dev dep
- `backend/tests/conftest.py` -- test_settings + client fixtures with SQLite + temp dir isolation
- `.gitignore` -- added `data/`

### Endpoints


| Method | Path                  | Status | Behavior                                                          |
| ------ | --------------------- | ------ | ----------------------------------------------------------------- |
| POST   | `/api/documents`      | 201    | Multipart upload, validates extension (.pdf/.txt/.md) + non-empty |
| GET    | `/api/documents`      | 200    | Returns `{documents: [...]}` ordered newest-first                 |
| DELETE | `/api/documents/{id}` | 204    | Removes DB row then file; 404 if not found                        |


### Validation

- Empty file -> 400 `"File is empty"`
- Unsupported extension -> 400 `"Unsupported file type: .exe. Allowed: .md, .pdf, .txt"`
- Delete nonexistent -> 404 `"Document not found"`

### Tests (12 total, all passing)

8 upload/list tests + 3 delete tests + 1 pre-existing health test. Covering: upload success, metadata correctness, file persistence on disk, empty list, multi-document list, empty file rejection, unsupported format rejection, PDF acceptance, delete success, delete disk cleanup, delete-nonexistent 404.

### Commits (5)

1. `docs(adr): add ADR 0002 for data storage strategy`
2. `feat(documents): add DB infrastructure, SQLAlchemy models, and Docker setup`
3. `feat(documents): add upload and list endpoints with tests`
4. `feat(documents): add delete endpoint tests and error cases`
5. `refactor(documents): clean up unused imports and safer delete ordering`

### Key Design Decisions

- **DB-first delete ordering**: Delete the DB row before removing the file from disk -- orphaned files are less harmful than broken DB references if a step fails
- **FastAPI dependency injection** for `get_settings()` and `get_session()` -- both overridable in tests via `app.dependency_overrides`
- **SQLite for tests, PostgreSQL for production** -- SQLAlchemy abstracts the difference; pgvector-specific tests can be added later

