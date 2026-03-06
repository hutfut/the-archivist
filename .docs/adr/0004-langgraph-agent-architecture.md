# 4. LangGraph Agent Architecture

**Date**: 2026-03-06  
**Status**: Accepted

## Context

The core feature of the application is a chat experience where an agent answers user questions based on uploaded document content. This requires retrieval-augmented generation (RAG): embed the user's query, find relevant document chunks via vector similarity, and generate a response grounded in those chunks.

Key decisions: how to orchestrate the RAG pipeline, how to handle the LLM (mock vs real), how to determine chunk relevance, how to persist conversations, and how to structure the API.

## Options considered

### Agent orchestration

1. **LangGraph `StateGraph`** — A typed, graph-based orchestration framework from the LangChain ecosystem. Nodes are functions that transform state; edges define flow with optional conditionals. Pros: explicit control flow, typed state, easy to test individual nodes, the graph is inspectable and extensible (add query rewriting, multi-step reasoning later). Cons: heavier abstraction than a plain function chain.

2. **Plain LangChain LCEL chain** — Compose retriever | prompt | LLM as a RunnableSequence. Pros: less code for a linear pipeline. Cons: conditional logic (e.g. "no relevant docs found") requires awkward branching, harder to test individual steps, doesn't demonstrate LangGraph as specified in the prompt.

3. **Custom Python pipeline** — No framework, just async functions. Pros: zero framework overhead, full control. Cons: doesn't satisfy the prompt's LangChain/LangGraph requirement, reinvents orchestration concerns.

### LLM strategy

1. **Mock-only (`FakeListLLM`)** — Returns canned responses from a list. Pros: zero setup. Cons: responses don't reflect the retrieved content, can't demonstrate that the pipeline actually passes context to the LLM.

2. **Custom `BaseChatModel` mock with context templating** — A mock that reads the retrieved chunks from its prompt and templates them into a structured response. Pros: demonstrates the full pipeline end-to-end (chunks appear in the response), testable, no external dependencies. Cons: responses aren't semantically meaningful.

3. **Real LLM via Ollama** — Run a local model (e.g. Llama 3) through `langchain-ollama`. Pros: real answers, impressive demo. Cons: requires Ollama installed and a model downloaded (~4+ GB), not guaranteed to be available on the reviewer's machine.

4. **Mock as default with config toggle for Ollama** — Combines options 2 and 3. The mock works out of the box; setting `LLM_PROVIDER=ollama` switches to a real model. Pros: works for everyone by default, supports real LLM for those who have it. Cons: slightly more code for the factory.

### Relevance grading

1. **LLM-based grading** — Ask the LLM to judge whether each chunk is relevant to the query. Pros: semantically meaningful filtering. Cons: doubles LLM calls, doesn't work with a mock LLM, adds latency.

2. **Cosine similarity threshold** — Discard chunks whose vector similarity score falls below a configurable threshold. Pros: functional with real embeddings, deterministic, fast, no LLM call needed. Cons: threshold is a heuristic that may not generalize across query types.

3. **No filtering** — Return whatever the vector search gives back. Pros: simplest. Cons: irrelevant chunks pollute the response, doesn't demonstrate conditional graph logic.

### Retrieval interface

1. **Direct SQLAlchemy query with pgvector `<=>` operator** — Raw cosine distance query against the chunks table. Pros: no extra dependency, full control over the query (JOIN with documents for filename). Cons: tighter coupling to pgvector SQL syntax.

2. **`langchain-postgres` `PGVector` wrapper** — LangChain's official PostgreSQL vector store integration. Pros: idiomatic LangChain interface, handles embedding and search. Cons: adds a dependency, may expect its own table schema rather than the existing chunks table.

### Source attribution storage

1. **JSON column on messages table** — Store `[{document_id, filename, chunk_content, similarity_score}]` as a JSON array on each assistant message. Pros: simple queries, no joins, self-contained. Cons: denormalized, chunk content duplicated.

2. **Separate join table** — `message_sources` table with FKs to messages and chunks. Pros: normalized, referential integrity. Cons: more tables, more complex queries, over-engineered for a single-user local app.

## Decision

- **Agent orchestration**: LangGraph `StateGraph` with three nodes — `retrieve_documents`, `grade_relevance`, `generate_response`. This is the simplest graph that genuinely uses LangGraph's conditional routing: `grade_relevance` routes to `generate_response` when relevant chunks are found, or directly to END with a "no relevant documents" message when none pass the threshold. The graph is easily extensible with query rewriting or multi-step reasoning nodes.

- **LLM strategy**: Custom `BaseChatModel` mock as default, with a config toggle for Ollama. The mock extracts retrieved context from the prompt and templates it into a response like "Based on your documents: [excerpts]. Sources: [filenames]". Setting `LLM_PROVIDER=ollama` and `OLLAMA_MODEL=<model>` switches to a real local LLM. This works for everyone out of the box while supporting real answers for reviewers with Ollama installed.

- **Relevance grading**: Cosine similarity threshold (configurable, default 0.3). Chunks below the threshold are discarded. This is functional with real embeddings and demonstrates the conditional edge in the graph without requiring an LLM for grading.

- **Retrieval interface**: Direct SQLAlchemy query with pgvector's `<=>` cosine distance operator, encapsulated behind a `RetrievalService` class. The initial plan was to use `langchain-postgres` `PGVectorStore`, but the wrapper is incompatible with the `chunks` table schema established in Milestone 3 (ADR 0003). Specifically:

  - `PGVectorStore` expects to manage its own table with a fixed schema (id, content, embedding, metadata JSONB). It cannot adopt an existing table with custom columns.
  - Our `chunks` table has a `document_id` FK to `documents` with `ON DELETE CASCADE`. This FK is critical — `delete_document` relies on PostgreSQL cascading the delete to chunks automatically. `PGVectorStore` doesn't support foreign keys on its tables, so we'd need manual cleanup logic.
  - `save_document` stores the document row, processes chunks, and stores embeddings in a single database transaction. If embedding fails, everything rolls back. With `PGVectorStore` managing its own table, this transactional consistency would be split across two write paths.
  - The `chunk_index` column is a typed integer in our schema. In `PGVectorStore`, it would live in a JSONB metadata blob — queryable but less clean.
  - Our schema is Alembic-managed. `PGVectorStore` creates tables itself, leaving a gap in the migration chain.

  Even if we had designed with the wrapper in mind from the start, these tradeoffs would still apply. The FK cascade, transactional consistency, and Alembic control are genuinely valuable for the document processing pipeline, and they're fundamentally incompatible with letting a library own the vector storage table. The direct query costs ~15 lines of SQL and gives full control over JOINs (chunks → documents for filename attribution), filtering, and index usage. The `RetrievalService` interface keeps the implementation swappable.

- **Source attribution**: JSON column on the messages table. Each assistant message stores its source attributions as a JSON array of `{document_id, filename, chunk_content, similarity_score}` objects. This avoids a join table that adds complexity without benefit for a local single-user app.

- **Conversation persistence**: New `conversations` and `messages` tables in PostgreSQL. Conversation title auto-generated from the first user message (truncated to 100 characters). Messages include role, content, optional sources JSON, and timestamps.

- **API design**: JSON responses only for this milestone. SSE streaming deferred to the frontend milestone where it provides actual UX value. Endpoints follow REST conventions: conversations as a resource with nested messages.

## Consequences

- **New dependencies**: `langgraph`, `langchain-core`, and `langchain-ollama` added to `pyproject.toml`. `langchain-postgres` is not needed since retrieval uses direct SQLAlchemy queries. The Ollama dependency is included in main deps so it's available when configured, but Ollama itself is not required to run the application.
- **Three-node graph is minimal but genuine**: The graph demonstrates LangGraph's value (conditional routing, typed state, testable nodes) without over-engineering. Additional nodes (query rewriting, summarization) can be added by inserting them into the graph without changing existing nodes.
- **Threshold-based grading is a heuristic**: The 0.3 default may need tuning. Making it configurable via `SIMILARITY_THRESHOLD` allows adjustment without code changes.
- **Mock LLM responses are structurally correct but not semantically meaningful**: The mock proves the pipeline works end-to-end. Real answer quality requires swapping in Ollama or another LLM provider.
- **JSON source storage is denormalized**: Chunk content is duplicated between the chunks table and the messages sources JSON. This is acceptable for a local app where storage is not a constraint, and it means source attributions survive even if the original document is deleted.
