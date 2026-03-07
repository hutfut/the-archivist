# 6. Hybrid Search and Retrieval Quality

**Date**: 2026-03-07  
**Status**: Accepted  
**Builds on**: ADR 0005 (RAG Retrieval Improvements)

## Context

After deploying Markdown-aware chunking and post-retrieval deduplication (ADR 0005), retrieval quality still suffers from cross-entity contamination. The query "what sort of skills does the witch use" returns chunks from Witchhunter, Mercenary, and Shadow pages because `all-MiniLM-L6-v2` embeds "witch" and "witchhunter" close together due to lexical overlap, and the word "skills" appears on every class page. Pure vector similarity cannot distinguish between these entities.

Three independent improvements are proposed: hybrid search, chunk context enrichment, and query rewriting.

## Options considered

### Hybrid search

1. **Vector-only (status quo)** — Cosine similarity on embeddings. Pros: simple. Cons: conflates semantically adjacent but contextually different terms ("witch" vs "witchhunter").

2. **BM25-only via PostgreSQL full-text search** — `tsvector`/`tsquery` with `ts_rank`. Pros: exact keyword matching distinguishes "witch" from "witchhunter". Cons: loses semantic understanding (synonyms, paraphrases).

3. **Hybrid: Vector + BM25 with Reciprocal Rank Fusion** — Run both queries, combine rankings with RRF (`score = 1/(k + rank)`). Pros: best of both -- semantic understanding from embeddings plus keyword precision from BM25. Cons: two queries per search, slightly more complex retrieval logic.

### Chunk context enrichment

1. **Embed raw content only (status quo)** — Chunk content is embedded as-is. Pros: simple. Cons: embedding has no signal about which document a chunk comes from.

2. **Prepend document title + section heading before embedding** — Embed `"Witch > Ascendancy classes: content..."` instead of just `"content..."`. Store the original content unchanged. Pros: embedding captures document identity, improving precision for entity-specific queries. Cons: requires re-processing all documents; prefix consumes some of the model's input window.

### Query rewriting

1. **No rewriting (status quo)** — Raw user question goes to search. Pros: simple, no LLM dependency. Cons: natural language questions are suboptimal as search queries.

2. **LLM-based multi-query rewriting** — A LangGraph node reformulates the query into 2-3 search-optimized variations before retrieval. With mock LLM, this is a passthrough. Pros: demonstrates LangGraph extensibility; with a real LLM, significantly improves recall. Cons: adds latency with a real LLM; no benefit with mock.

## Decision

- **Hybrid search**: Option 3 — Vector + BM25 with RRF. Add a `search_vector` tsvector column (GIN-indexed) to the chunks table, populated at ingestion time. At query time, run both vector similarity and full-text search, combine with RRF (k=60). RRF scores are normalized to [0, 1] so the similarity threshold works uniformly across retrieval modes. Keyword search uses OR logic (combining per-word `plainto_tsquery` with `||`) so natural language questions with many terms still match partial content. Configurable via `RETRIEVAL_MODE` env var (`"hybrid"`, `"vector"`, `"keyword"`; default `"hybrid"`).

- **Chunk context enrichment**: Option 2 was implemented and tested but **reverted**. `all-MiniLM-L6-v2` is a symmetric model -- prepending a title prefix to documents (but not queries) catastrophically reduced cosine similarity (from ~0.8 to 0.016). The `build_embedding_text` utility remains in the codebase for future use with asymmetric retrieval models (e.g., BGE, E5). Hybrid search provides the keyword-level entity discrimination that enrichment was intended to deliver.

- **Query rewriting**: Option 2 — New `rewrite_query` node in the LangGraph agent. Passthrough with mock LLM, multi-query with Ollama. Results from multiple queries are merged and deduplicated.

## Consequences

- **Schema migration required**: New nullable `search_vector` column on `chunks` with a GIN index.
- **Re-seed required**: All documents must be re-processed to populate tsvector columns.
- **No new Python dependencies**: PostgreSQL full-text search, `to_tsvector`, `ts_rank` are built-in. SQLAlchemy already exposes `func.to_tsvector` and `func.ts_rank`.
- **Two queries per search in hybrid mode**: Negligible performance impact for the corpus size (~153 documents). Each query hits an index (GIN for tsvector, IVFFlat/HNSW for vector).
- **Backward compatible**: `RETRIEVAL_MODE=vector` reproduces the pre-change behavior exactly.
- **Query rewriting is a no-op with mock LLM**: The node exists in the graph (testable, demonstrates extensibility) but doesn't alter the query.
- **Embedding enrichment deferred**: The symmetric embedding model cannot benefit from document-level prefixes without also prefixing queries. This would work with asymmetric models and is documented as a future improvement.
