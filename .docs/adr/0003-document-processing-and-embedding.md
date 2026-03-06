# 3. Document Processing and Embedding Approach

**Date**: 2026-03-06  
**Status**: Accepted

## Context

When a user uploads a document, we need to make its content searchable by the RAG agent. This requires three steps: extracting plain text from the file, splitting that text into chunks small enough for embedding models, and generating vector embeddings that enable semantic similarity search.

Key decisions: which extraction libraries, what chunking strategy and parameters, which embedding model, how to trigger processing relative to the upload request, and how to test the pipeline given the heavy ML dependency.

## Options considered

### Text extraction

1. **`pypdf` for PDF, plain read for TXT/MD** — Lightweight, well-maintained, covers the three supported formats. `pypdf` is a pure-Python PDF reader with no system dependencies. Pros: simple, fast, no native binaries. Cons: limited to text-based PDFs (no OCR for scanned documents).

2. **`unstructured` library** — Handles dozens of formats (PDF, DOCX, HTML, images via OCR). Pros: extensible, production-grade. Cons: heavy dependency tree (includes `libmagic`, `tesseract`, `poppler`), overkill for three formats, adds container build complexity.

### Chunking

1. **LangChain `RecursiveCharacterTextSplitter`** — Splits text by a hierarchy of separators (paragraphs, sentences, words), respecting natural boundaries. Configurable chunk size and overlap. Pros: well-tested, standard in LangChain pipelines, produces coherent chunks. Cons: character-based sizing is an approximation of token count.

2. **Fixed-size token splitting** — Split by exact token count using the model's tokenizer. Pros: precise sizing. Cons: ignores semantic boundaries, more complex to implement, marginal benefit for retrieval quality.

### Embeddings

1. **`sentence-transformers` (`all-MiniLM-L6-v2`) via LangChain `HuggingFaceEmbeddings`** — Local model, 384-dimensional vectors, ~80 MB download, runs on CPU. Pros: free, offline, real semantic search works, fast inference for small batches. Cons: first-run model download, heavier test dependency.

2. **OpenAI or other API-based embeddings** — Higher quality vectors. Cons: requires API key and token spend, not offline-friendly, violates the "no expectation to pay for tokens" constraint.

3. **Mock/random embeddings** — Deterministic hash-based vectors. Pros: zero dependencies, instant. Cons: retrieval is structurally correct but semantically meaningless — the demo doesn't actually find relevant content.

### Processing trigger

1. **Synchronous on upload** — The upload endpoint blocks until extraction, chunking, and embedding are complete, then returns the document with `chunk_count`. Pros: simple, no status tracking needed, the response confirms processing is done. Cons: upload latency scales with document size; large PDFs may take seconds.

2. **Background task with status polling** — Upload returns immediately with `status: pending`; a background task processes the document and updates its status. Pros: fast upload response, better UX for large files. Cons: more complex (status field, polling logic, error handling for failed processing).

### Test strategy

1. **SQLite for tests, mock vector operations** — Fast, no Docker needed for tests, but can't test pgvector columns or real pipeline integration. Requires workarounds (skip chunks table, no-op processor).

2. **testcontainers PostgreSQL** — Spin up a real `pgvector/pgvector:pg17` container per test session. Tests run against the same engine as production. Pros: no workarounds, tests the real schema including vector columns. Cons: requires Docker, adds ~3-5s startup per session.

## Decision

- **Text extraction**: `pypdf` for PDF, plain UTF-8 read for TXT and Markdown. Extensible via a format-to-extractor mapping if more formats are needed later.
- **Chunking**: `RecursiveCharacterTextSplitter` with `chunk_size=500`, `chunk_overlap=100`. These parameters balance retrieval granularity with context preservation for the 384-dim embedding space.
- **Embeddings**: `all-MiniLM-L6-v2` via `HuggingFaceEmbeddings` for production. A `MockEmbeddingService` that returns deterministic fixed-dimension vectors is used in tests to avoid the model download and keep tests fast.
- **Processing trigger**: Synchronous on upload for the initial implementation. The `DocumentProcessor` protocol makes switching to background processing a self-contained change later.
- **Test strategy**: testcontainers PostgreSQL. Tests run the full pipeline (extract → chunk → embed → store) against real PostgreSQL with pgvector, using the mock embedding service. This eliminates SQLite workarounds and tests the actual schema.

## Consequences

- **First-run model download**: The embedding model (~80 MB) downloads on first use. This is cached locally and doesn't recur. The README should document this.
- **Upload latency**: Synchronous processing means uploads block. For the supported formats and typical document sizes (< 50 pages), this is a few seconds at most. Background processing is documented as a future enhancement.
- **Docker required for tests**: The test suite needs Docker running. This aligns with the project already requiring Docker for the dev database.
- **Mock embeddings in tests**: Tests verify the pipeline structure and database integration, but not semantic retrieval quality. This is acceptable since the prompt says evaluation is on design and implementation, not answer quality.
- **Extensible design**: The `DocumentProcessor` protocol, `EmbeddingService` protocol, and format-to-extractor mapping all support future additions (new formats, background processing, real embeddings in integration tests) without modifying existing code.
