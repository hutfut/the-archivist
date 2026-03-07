---
name: Backend Gap Remediation
overview: "Address reviewer-identified gaps in the NotebookLM backend service across 4 milestones: correctness fixes, safety/robustness, async hygiene, and API polish."
todos:
  - id: m1-correctness
    content: "Milestone 1: Correctness fixes -- SourceAttribution model, schema management, content-type derivation, missing __init__.py, dirty files, API-layer logging"
    status: pending
  - id: m2-safety
    content: "Milestone 2: Safety and robustness -- max upload size, parameterized vector query, conversation history truncation"
    status: pending
  - id: m3-async
    content: "Milestone 3: Async hygiene -- ainvoke in graph nodes, thread-offloaded processing, streaming comment"
    status: pending
  - id: m4-polish
    content: "Milestone 4: API polish -- pagination on list endpoints, .env.example"
    status: pending
isProject: false
---

# Backend Gap Remediation Plan

## 1. Requirements Summary

From [.docs/PROMPT.md](.docs/PROMPT.md) and self-review against [.cursor/rules/code-review.mdc](.cursor/rules/code-review.mdc):

- Code should be **production-quality**: proper error handling, input validation, no hidden gotchas
- **Correctness > readability > extensibility > performance** (from [.cursor/rules/assessment.mdc](.cursor/rules/assessment.mdc))
- Every commit must leave the project in a **buildable, runnable state**
- Tests must pass and cover new/changed behavior
The gaps below were identified by reviewing the backend as a take-home assessment evaluator would.

## 2. Ambiguities and Assumptions


| Area              | Ambiguity                                                                                            | Assumption                                                                                                                                                                                    |
| ----------------- | ---------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Schema management | Alembic migrations exist alongside `Base.metadata.create_all` in `session.py` -- which is canonical? | Remove `create_all` from app startup; rely on Alembic for production. Keep `create_all` in test fixtures only (faster, no migration files needed for unit tests).                             |
| Streaming         | Current SSE endpoint runs the full agent then fake-streams the result. Is real streaming required?   | Keep the current approach for mock LLM (real streaming is impossible with `FakeListLLM`). Add a code comment explaining the limitation and how to switch to `astream_events` with a real LLM. |
| Pagination        | List endpoints return all records. Is pagination needed for a local demo?                            | Add optional `limit`/`offset` query params with sensible defaults. Low effort, high signal to a reviewer.                                                                                     |
| File size limits  | No max upload size. Is this a risk for a local-only app?                                             | Add a configurable max (default 50 MB). Prevents accidental OOM and signals awareness.                                                                                                        |


## 3. High-Level Architecture

No structural changes. All work is within existing modules:

- **Key files modified**: `[backend/app/api/documents.py](backend/app/api/documents.py)`, `[backend/app/api/conversations.py](backend/app/api/conversations.py)`, `[backend/app/services/retrieval.py](backend/app/services/retrieval.py)`, `[backend/app/services/document_service.py](backend/app/services/document_service.py)`, `[backend/app/agent/graph.py](backend/app/agent/graph.py)`, `[backend/app/db/session.py](backend/app/db/session.py)`, `[backend/app/models/conversation.py](backend/app/models/conversation.py)`, `[backend/app/config.py](backend/app/config.py)`
- **New file**: `.env.example`

## 4. ADRs to Write

None. These are correctness/quality fixes within existing architecture, not structural decisions.

## 5. Milestones

### Milestone 1: Correctness fixes and API-layer logging

**Goal**: Eliminate data correctness bugs, schema management inconsistencies, and the logging blind spot at the API boundary.

**Implementation details**:

- Add `section_heading` field to `SourceAttribution` Pydantic model in `[backend/app/models/conversation.py](backend/app/models/conversation.py)` -- data is already returned by the agent but silently dropped during serialization
- Remove `Base.metadata.create_all` and `CREATE EXTENSION` from `[backend/app/db/session.py](backend/app/db/session.py)` `init_db()` -- production startup should rely on Alembic; the test `conftest.py` already handles schema setup independently
- Derive `content_type` from file extension in the upload endpoint rather than trusting the client-supplied MIME type (disconnect between extension validation and MIME-based extraction)
- Add `__init__.py` to `backend/app/api/` and `backend/app/agent/` for explicit package convention
- Commit or discard the 3 dirty `__init__.py` files (`db/`, `models/`, `services/`)
- Add structured logging to the API layer:
  - `documents.py`: add `logger`, log on upload (filename, size), delete (doc_id), and validation rejections (extension, empty file)
  - `conversations.py`: log on create, delete, send_message (conversation_id, query length), and stream start/end
  - `health.py`: no logging needed (too noisy)
  - `db/session.py`: log on `init_db` (database URL with password masked) and `close_db`

**Tests**:

- Existing `test_conversations.py` tests validate that `section_heading` now appears in source attributions
- Upload a `.md` file with `content_type: text/plain` and verify it's processed as markdown
- All existing tests still pass

**Commits**: ~3 (model/schema fixes, content-type derivation, API-layer logging)

---

### Milestone 2: Safety and robustness

**Goal**: Input validation and query safety hardened at system boundaries.

**Implementation details**:

- Add configurable `max_upload_size` to `Settings` (default 50 MB); validate in `_validate_upload()` in `[backend/app/api/documents.py](backend/app/api/documents.py)`
- Replace raw SQL string interpolation in `[backend/app/services/retrieval.py](backend/app/services/retrieval.py)` `_vector_search` with parameterized query or pgvector's SQLAlchemy operator (`Chunk.embedding.cosine_distance(...)`)
- Add conversation history truncation: introduce `max_history_messages` setting, apply in `get_conversation_history()` to prevent unbounded context growth

**Tests**:

- Upload a file exceeding max size, verify 400 response
- Vector search still returns correct results after parameterization
- Conversation with many messages only sends the last N to the agent

**Commits**: ~3 (upload size limit, parameterized vector query, history truncation)

---

### Milestone 3: Async hygiene

**Goal**: CPU-bound and synchronous I/O work no longer blocks the async event loop.

**Implementation details**:

- In `[backend/app/agent/graph.py](backend/app/agent/graph.py)`: change `llm.invoke()` to `llm.ainvoke()` in both `_build_rewrite_node` and `_build_generate_node` (the rewrite node function also needs to become `async`)
- In `[backend/app/services/processing.py](backend/app/services/processing.py)`: wrap `extract_text()` and `embed_texts()` calls in `asyncio.to_thread()` to offload CPU-bound work
- Add a clarifying comment on the SSE streaming endpoint explaining the fake-streaming limitation and the path to real streaming with `astream_events`

**Tests**:

- Agent tests still pass with `ainvoke` (mock LLM supports both sync and async)
- Document upload with a real fixture still produces correct chunk counts

**Commits**: ~2 (async LLM calls, thread-offloaded processing)

---

### Milestone 4: API polish

**Goal**: List endpoints support pagination; error responses are consistent; config is documented.

**Implementation details**:

- Add `limit` (default 50) and `offset` (default 0) query params to `GET /api/documents` and `GET /api/conversations`
- Add configurable `log_level` to `Settings` (default `INFO`, read from `LOG_LEVEL` env var); use it in `logging.basicConfig` in `main.py` instead of the hardcoded `logging.INFO`
- Create `.env.example` at project root documenting all environment variables from `[backend/app/config.py](backend/app/config.py)` (including `LOG_LEVEL`)
- Add structured error response model (optional -- only if low effort; the default FastAPI `{"detail": ...}` is acceptable for a demo)

**Tests**:

- Pagination: upload 3 docs, request with `limit=2`, verify 2 returned; request with `offset=2`, verify 1 returned
- Same for conversations

**Commits**: ~2 (pagination, .env.example)

## 6. Dependency Summary

No new dependencies. All changes use existing libraries (FastAPI, SQLAlchemy, pgvector, LangChain/LangGraph, sentence-transformers).