---
name: Backend Gap Remediation v2
overview: "Address 15 reviewer-identified gaps in the NotebookLM backend across 4 milestones: correctness fixes, API robustness, chat workflow refactor, and observability."
todos:
  - id: m1-correctness
    content: "Milestone 1: Correctness fixes -- double file read, delete guard, embed_query async, message atomicity, agent error handling"
    status: completed
  - id: m2-robustness
    content: "Milestone 2: API robustness -- health DB check, CORS tightening, pagination totals, missing __init__.py"
    status: completed
  - id: m3-refactor
    content: "Milestone 3: Chat workflow refactor -- extract shared logic, MockChatModel async, UUID path params, session docs"
    status: completed
  - id: m4-observability
    content: "Milestone 4: Observability and doc hygiene -- ADR index, request correlation ID"
    status: completed
isProject: false
---

# Backend Gap Remediation v2

## 1. Requirements Summary

From [.docs/PROMPT.md](.docs/PROMPT.md) and self-review against [.cursor/rules/code-review.mdc](.cursor/rules/code-review.mdc):

- Code must be **production-quality**: proper error handling, input validation, no hidden gotchas
- **Correctness > readability > extensibility > performance** (from [.cursor/rules/assessment.mdc](.cursor/rules/assessment.mdc))
- Every commit must leave the project in a **buildable, runnable state**
- Tests must pass and cover new/changed behavior
- Public interfaces must have **clear contracts**; errors handled and surfaced

15 gaps were identified by reviewing the backend as a take-home assessment evaluator would. They span correctness, robustness, code hygiene, and observability. The root README will be created separately after these improvements land.

## 2. Ambiguities and Assumptions


| Area                | Ambiguity                                                                                       | Assumption                                                                                                                                              |
| ------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Message atomicity   | Should the user message be visible immediately, or only after the agent succeeds?               | Defer both user and assistant message commits until the agent completes. If the agent fails, no partial state is persisted. The user can retry cleanly. |
| Health check depth  | Should the health endpoint verify all dependencies (DB, embedding model) or just liveness?      | Add a DB connectivity check (execute `SELECT 1`). Skip embedding model check -- it's loaded at startup and would add latency to every health poll.      |
| Chat workflow dedup | Should streaming and non-streaming share a service method, or should one delegate to the other? | Extract a `run_agent_turn` service function that both endpoints call. The streaming endpoint wraps the result in SSE chunking afterward.                |
| Correlation ID      | Should the correlation ID be a response header, a log field, or both?                           | Both. Generate a UUID per request, attach via `contextvars` to all log lines, and return it as `X-Request-ID` response header.                          |


## 3. High-Level Architecture

No structural changes to the module layout. All work is within existing modules.

**Key modules modified**:

- `backend/app/api/documents.py` -- pass bytes instead of re-reading file
- `backend/app/api/conversations.py` -- delegate to service, error handling
- `backend/app/api/health.py` -- add DB check
- `backend/app/services/document_service.py` -- accept bytes, guard file deletion
- `backend/app/services/conversation_service.py` -- new `run_agent_turn` method
- `backend/app/services/retrieval.py` -- async `embed_query`
- `backend/app/agent/llm.py` -- add `_agenerate` override
- `backend/app/main.py` -- tighten CORS, add correlation ID middleware
- `backend/app/models/document.py` -- add `total` to list response
- `backend/app/models/conversation.py` -- add `total` to list response

**New files**:

- `backend/app/__init__.py`, `backend/app/api/__init__.py`, `backend/app/agent/__init__.py` -- empty package markers

## 4. ADRs to Write

None. These are correctness/quality fixes within existing architecture, not structural decisions.

## 5. Milestones

### Milestone 1: Correctness fixes

**Goal**: Eliminate data correctness bugs and event-loop-blocking code on the critical path.

**Implementation details**:

- **Double file read** (`[documents.py](backend/app/api/documents.py)`, `[document_service.py](backend/app/services/document_service.py)`): Read file bytes once in the upload handler; pass `bytes` to `save_document` instead of `UploadFile`. Change `save_document` signature to accept `(filename: str, content: bytes, session, settings, processor)`.
- **Delete file guard** (`[document_service.py](backend/app/services/document_service.py)`): Wrap `shutil.rmtree` in `try/except OSError` with `logger.warning`. The DB commit stays first (file orphans are less harmful than dangling DB records pointing to missing files).
- **Async `embed_query**` (`[retrieval.py](backend/app/services/retrieval.py)`): Wrap `self._embedding_service.embed_query(query)` in `await asyncio.to_thread(...)` inside `_vector_search`. This unblocks the event loop for the ~50-100ms embedding inference.
- **Message atomicity + agent error handling** (`[conversations.py](backend/app/api/conversations.py)`, `[conversation_service.py](backend/app/services/conversation_service.py)`): Defer `session.commit()` in `add_message` -- accept an optional `commit=True` parameter (default True for backward compat). In the chat path, save user message with `commit=False`, invoke agent, save assistant message, then commit once. Wrap `agent.ainvoke` in `try/except Exception` -- on failure, roll back the session and return a structured 502 error.

**Tests**:

- Upload a file and verify `save_document` receives bytes directly (mock or inspect)
- Delete a document whose file directory has already been removed; verify 204 (not 500)
- Agent invocation that raises `RuntimeError`; verify user message is not persisted and response is structured JSON with status 502
- Existing retrieval tests still pass with async `embed_query`

**Commits**: ~4 (double-read fix, delete guard, async embed, message atomicity + error handling)

---

### Milestone 2: API robustness

**Goal**: Health check reflects real readiness, CORS is locked down, pagination is client-friendly, packages are consistent.

**Implementation details**:

- **Health check DB verification** (`[health.py](backend/app/api/health.py)`): Inject a DB session dependency, execute `SELECT 1`. Return `{"status": "ok"}` on success, `{"status": "degraded", "detail": "..."}` with 503 on failure.
- **CORS tightening** (`[main.py](backend/app/main.py)`): Change `allow_methods` to `["GET", "POST", "DELETE", "OPTIONS"]` and `allow_headers` to `["Content-Type", "Accept"]`.
- **Pagination totals** (`[document.py](backend/app/models/document.py)`, `[conversation.py](backend/app/models/conversation.py)`, `[document_service.py](backend/app/services/document_service.py)`, `[conversation_service.py](backend/app/services/conversation_service.py)`): Add `total: int` field to `DocumentListResponse` and `ConversationListResponse`. Run `select(func.count()).select_from(Model)` alongside the data query and return both.
- **Missing `__init__.py**`: Create empty `backend/app/__init__.py`, `backend/app/api/__init__.py`, `backend/app/agent/__init__.py`.

**Tests**:

- Health check with a valid DB returns 200 and `{"status": "ok"}`
- (Difficult to test DB-down in integration; verify the query runs at minimum)
- Upload 3 documents, `GET /api/documents?limit=2` returns `total: 3` with 2 items
- Same pattern for conversations
- All existing tests still pass after CORS change

**Commits**: ~3 (health check + CORS, pagination totals, `__init__.py` files)

---

### Milestone 3: Chat workflow refactor and polish

**Goal**: Streaming and non-streaming chat endpoints share a single code path; mock LLM is properly async; path params are type-safe.

**Implementation details**:

- **Extract shared chat workflow** (`[conversation_service.py](backend/app/services/conversation_service.py)`, `[conversations.py](backend/app/api/conversations.py)`): Create `async def run_agent_turn(conversation_id, content, agent, session_factory, max_history_messages) -> MessageResponse` in `conversation_service`. This method handles: validate conversation exists, save user message, get history, invoke agent (with try/except), save assistant message, set title, commit. Both `send_message` and `_stream_response` call this method. The streaming endpoint then chunks the response text into SSE events.
- `**MockChatModel._agenerate**` (`[llm.py](backend/app/agent/llm.py)`): Add `async def _agenerate(...)` that calls the same formatting logic directly, avoiding thread dispatch.
- **UUID path parameters** (`[conversations.py](backend/app/api/conversations.py)`, `[documents.py](backend/app/api/documents.py)`): Change `conversation_id: str` and `document_id: str` to `conversation_id: UUID` / `document_id: UUID` in route signatures. Convert to `str` internally where needed (DB queries).
- **Session management comment**: Add a docstring to `_stream_response` explaining why it creates its own sessions from the factory instead of using FastAPI DI.

**Tests**:

- All existing conversation and streaming tests still pass after refactor
- `POST /api/conversations/not-a-uuid/messages` returns 422 (not 404)
- `DELETE /api/documents/not-a-uuid` returns 422

**Commits**: ~3 (extract `run_agent_turn`, mock async + UUID params, session comment)

---

### Milestone 4: Observability and doc hygiene

**Goal**: ADR index is current and request logs are traceable across concurrent requests.

**Implementation details**:

- **ADR index** (`[.docs/adr/README.md](.docs/adr/README.md)`): Add entries for ADR 0005 (RAG retrieval improvements) and ADR 0006 (hybrid search and retrieval quality).
- **Request correlation ID** (`[main.py](backend/app/main.py)`): Add a Starlette middleware that generates a UUID per request, stores it in `contextvars`, adds it to a custom `logging.Filter` so all log lines include `[request_id=...]`, and sets the `X-Request-ID` response header.

**Tests**:

- Verify `X-Request-ID` header is present on any response
- Verify log output includes the request ID (capture log records in test)

**Commits**: ~2 (ADR index, correlation ID middleware)

## 6. Dependency Summary

No new dependencies. All changes use existing libraries:

**Backend**:

- `fastapi` / `starlette` -- CORS config, middleware, health endpoint
- `sqlalchemy` -- session management, `func.count()` for pagination totals
- `asyncio` -- `to_thread` for embedding offload
- `contextvars` + `logging` -- request correlation ID (stdlib)
- `uuid` -- correlation ID generation (stdlib)

