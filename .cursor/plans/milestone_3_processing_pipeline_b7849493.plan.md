---
name: Milestone 3 Processing Pipeline
overview: "Pivot test infrastructure from SQLite to testcontainers PostgreSQL, then add a document processing pipeline: text extraction, chunking, embeddings via sentence-transformers, and pgvector storage. Processing is triggered synchronously on upload."
todos:
  - id: m3-adr
    content: Write ADR 0003 (document processing and embedding approach) and update the ADR index
    status: completed
  - id: m3-testcontainers
    content: "Pivot tests from SQLite to testcontainers PostgreSQL: add testcontainers dep, rewrite conftest.py with session-scoped pgvector container, verify all existing tests pass"
    status: completed
  - id: m3-extraction
    content: Add text extraction service (pypdf for PDF, plain read for TXT/MD) with unit tests and sample fixtures
    status: completed
  - id: m3-chunking
    content: Add chunking logic using RecursiveCharacterTextSplitter with unit tests
    status: completed
  - id: m3-embedding
    content: Add EmbeddingService protocol with HuggingFace and Mock implementations
    status: completed
  - id: m3-chunk-model
    content: Add Chunk SQLAlchemy model with pgvector Vector(384) column and Alembic migration
    status: completed
  - id: m3-pipeline
    content: "Wire DocumentProcessor into upload/delete flow: extract -> chunk -> embed -> store, update chunk_count"
    status: completed
  - id: m3-self-review
    content: Self-review against code-review checklist, run full test suite, make commits
    status: completed
isProject: false
---

# Milestone 3: Document Processing Pipeline

## Key Decisions

- **pgvector** for vector storage (per ADR 0002 -- single database, no ChromaDB)
- **Real embeddings** (`sentence-transformers/all-MiniLM-L6-v2`, 384 dimensions) for production; **mock embeddings** injected for tests
- **Synchronous processing** on upload (acceptable for local single-user)
- **testcontainers PostgreSQL** for all tests -- eliminates SQLite workarounds, tests run against the same database engine as production
- `**DocumentProcessor` protocol** for dependency injection -- production uses the full pipeline, tests use `PipelineProcessor` with `MockEmbeddingService`

## Extensibility for Future Creative Additions

The design deliberately leaves room for additions tracked in the [master plan](../../.cursor/plans/notebooklm_implementation_plan_c45168f4.plan.md) Milestone 7:

- **Processing status / background processing**: The `DocumentProcessor` protocol isolates processing from the upload handler. Switching from sync to `BackgroundTasks` + adding a `status` field is a self-contained change. The frontend polls `GET /api/documents/{id}` to track progress -- no event bus needed for a single-producer single-consumer local app. Tests already run against real PostgreSQL, so no compatibility issues.
- **Duplicate detection**: Adding a `content_hash` column to `Document` and a hash check before save is additive -- doesn't require changing the processing pipeline.
- **Document statistics**: `extract_text()` returns plain text; wrapping it in a result dataclass with `word_count`/`page_count` is a small extension.
- **Chunk provenance**: Adding `start_char`/`end_char` to the `Chunk` model and tracking offsets during chunking is additive -- the chunking function can be extended to return offsets without changing its callers.

## Test Infrastructure Pivot: SQLite -> testcontainers PostgreSQL

Currently [conftest.py](backend/tests/conftest.py) creates a throwaway SQLite database per test. This prevents testing pgvector columns and means tests run against a different database engine than production. The pivot replaces SQLite with a **session-scoped pgvector PostgreSQL container** via `testcontainers-python`.

**New conftest structure:**

- `pg_container` (session-scoped) -- starts `pgvector/pgvector:pg17` once per test run
- `database_url` (session-scoped) -- constructs `postgresql+asyncpg://` URL from the container
- `test_settings` (function-scoped) -- `Settings` with the real PostgreSQL URL and a temp `upload_dir`
- `client` (function-scoped) -- creates tables via `init_db`, yields the test client, then **drops all tables** on teardown for isolation

**Why this ordering works:** The pivot is a standalone commit. Existing M1/M2 tests pass unchanged against PostgreSQL -- they don't use SQLite-specific behavior. The processing pipeline work that follows naturally uses pgvector without workarounds.

**Trade-off:** Tests now require Docker running. This is acceptable because the project already requires Docker for the dev PostgreSQL (docker-compose.yml). Test suite startup adds ~3-5 seconds for the container, but the container is reused across all tests in a session.

## Architecture

```mermaid
flowchart LR
    Upload["POST /api/documents"] --> Save["Save file to disk"]
    Save --> Extract["extract_text()"]
    Extract --> Chunk["chunk_text()"]
    Chunk --> Embed["EmbeddingService.embed_texts()"]
    Embed --> Store["Store Chunk rows in PostgreSQL"]
    Store --> UpdateDoc["Update document.chunk_count"]
```



## New Files

### 1. ADR 0003 -- [.docs/adr/0003-document-processing-and-embedding.md](.docs/adr/0003-document-processing-and-embedding.md)

Covers: text extraction strategy, chunking parameters, embedding model choice, pgvector storage, synchronous processing trade-off.

### 2. Text extraction -- [backend/app/services/text_extraction.py](backend/app/services/text_extraction.py)

```python
def extract_text(file_path: Path, content_type: str) -> str:
    """Extract plain text from a supported file format."""
```

- PDF: `pypdf.PdfReader` -- iterate pages, join text
- TXT/MD: read as UTF-8
- Raises `ValueError` for unsupported types

### 3. Embedding service -- [backend/app/services/embedding.py](backend/app/services/embedding.py)

```python
class EmbeddingService(Protocol):
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, query: str) -> list[float]: ...

class HuggingFaceEmbeddingService:  # production -- all-MiniLM-L6-v2
class MockEmbeddingService:         # tests -- deterministic fixed-dimension vectors
```

`embed_query` is exposed now for Milestone 4 (retrieval), even though M3 only uses `embed_texts`.

### 4. Document processor -- [backend/app/services/processing.py](backend/app/services/processing.py)

```python
class DocumentProcessor(Protocol):
    async def process(self, doc_id: str, file_path: Path, content_type: str, session: AsyncSession) -> int: ...

class PipelineProcessor:      # production + tests: extract -> chunk -> embed -> store
```

- Chunking uses `langchain_text_splitters.RecursiveCharacterTextSplitter` with `chunk_size=500`, `chunk_overlap=100`
- Returns chunk count so the caller can update `document.chunk_count`
- Tests use `PipelineProcessor` with `MockEmbeddingService` -- the full pipeline runs against real PostgreSQL, only the embedding model is swapped

### 5. Chunk model + migration

**Model** in [backend/app/db/models.py](backend/app/db/models.py):

```python
class Chunk(Base):
    __tablename__ = "chunks"
    id: Mapped[str]             # UUID PK
    document_id: Mapped[str]    # FK -> documents.id, ON DELETE CASCADE
    chunk_index: Mapped[int]
    content: Mapped[str]        # Text
    embedding                   # Vector(384)
    created_at: Mapped[datetime]
```

**Migration** `0002_create_chunks_table.py`: enables `vector` extension, creates `chunks` table, adds index on `document_id`.

### 6. Test files

- `backend/tests/test_text_extraction.py` -- PDF/TXT/MD extraction, empty file, unsupported format
- `backend/tests/test_processing.py` -- chunking logic (chunk sizes, overlap, short text), embedding mock verification
- `backend/tests/fixtures/` -- small sample files (sample.pdf, sample.txt, sample.md)

## Modified Files


| File                                                                                 | Change                                                                                                                                                         |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [backend/pyproject.toml](backend/pyproject.toml)                                     | Add `testcontainers[postgres]` to dev deps; add `pypdf`, `langchain-text-splitters`, `langchain-huggingface`, `sentence-transformers`, `pgvector` to main deps |
| [backend/app/db/models.py](backend/app/db/models.py)                                 | Add `Chunk` model with `Vector(384)`                                                                                                                           |
| [backend/app/services/document_service.py](backend/app/services/document_service.py) | Accept `DocumentProcessor`, call `processor.process()` after saving file, update `chunk_count`                                                                 |
| [backend/app/api/documents.py](backend/app/api/documents.py)                         | Add `DocumentProcessor` as a FastAPI dependency on the upload endpoint                                                                                         |
| [backend/app/main.py](backend/app/main.py)                                           | Initialize `HuggingFaceEmbeddingService` and `PipelineProcessor` on startup; register as dependency                                                            |
| [backend/app/config.py](backend/app/config.py)                                       | Add `embedding_model` setting (default `all-MiniLM-L6-v2`)                                                                                                     |
| [backend/tests/conftest.py](backend/tests/conftest.py)                               | Replace SQLite with testcontainers PostgreSQL; add `MockEmbeddingService` + `PipelineProcessor` overrides                                                      |
| [.docs/adr/README.md](.docs/adr/README.md)                                           | Add ADR 0003 to the index table                                                                                                                                |


## Commit Plan

1. `docs(adr): add ADR 0003 for document processing and embedding` -- ADR file + README index update
2. `test(infra): switch from SQLite to testcontainers PostgreSQL` -- add `testcontainers[postgres]` dep, rewrite conftest.py with session-scoped pgvector container, drop-all teardown for isolation; remove `aiosqlite` dev dep; verify all existing tests pass unchanged
3. `feat(processing): add text extraction and chunking with tests` -- text_extraction.py, chunking logic, test fixtures, test_text_extraction.py, test_processing.py (chunking tests), pyproject.toml deps (pypdf, langchain-text-splitters)
4. `feat(processing): add embedding service, chunk model, and pipeline integration` -- embedding.py, processing.py, Chunk model, migration, document_service integration, API wiring, config update, conftest mock embedding override, remaining deps

