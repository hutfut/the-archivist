# 5. RAG Retrieval Quality Improvements

**Date**: 2026-03-07  
**Status**: Accepted  
**Supersedes**: Chunking parameters from ADR 0003

## Context

With real wiki content loaded via the seed script, retrieval quality is poor. The top-k results returned to the LLM are fragmented, duplicated, and lack structural context. Specific failure modes:

1. **Fragmented chunks** — 500-character chunks split mid-section, so a concept like "how damage is calculated" is scattered across many small pieces. The LLM receives incomplete context.
2. **Duplicate slots wasted** — Overlapping character-based splits produce near-identical chunks that both land in the top-k, crowding out diverse results.
3. **No structural awareness** — The chunker treats Markdown as flat text, ignoring `#` / `##` / `###` headers that delineate logical sections.

These are chunking and retrieval problems, not LLM problems. Fixing them is prerequisite to coherent answers regardless of which LLM is used.

## Options considered

### Chunking strategy

1. **Increase chunk size only** — Raise `DEFAULT_CHUNK_SIZE` from 500 to 1000+. Pros: trivial change, fewer fragments. Cons: still splits on arbitrary character boundaries within sections; no structural metadata.

2. **Markdown-aware chunking (header splitting + size fallback)** — First pass splits on `#`, `##`, `###` headers via `MarkdownHeaderTextSplitter`, keeping each section as a coherent unit. Second pass sub-splits sections that exceed the max chunk size via `RecursiveCharacterTextSplitter`. Store the header hierarchy as metadata. Pros: chunks align with document structure, metadata enables richer context for the LLM. Cons: only benefits Markdown files; slightly more complex pipeline.

3. **Parent-child retrieval** — Embed small chunks for precise matching, but return the larger parent section on match. Pros: best of both worlds (precise search, rich context). Cons: requires two tiers of stored chunks, parent-child DB relationship, and more complex retrieval logic. The marginal gain over option 2 is small since section-aware chunking already keeps sections coherent.

### Deduplication strategy

1. **No dedup (status quo)** — Trust the vector search ordering. Cons: overlapping chunks waste top-k slots with near-identical content.

2. **Post-retrieval dedup (merge adjacent + drop overlapping)** — Over-fetch candidates, then merge consecutive chunks from the same document and drop chunks with high token overlap. Pros: diverse results, richer merged context. Cons: adds a processing step; merged chunks are longer than originals.

3. **Cross-encoder reranking** — Over-fetch, then rerank with a cross-encoder model. Pros: best relevance ranking. Cons: adds a second ML model dependency (~100 MB), increases query latency, and the root problem is chunking quality, not ranking quality.

### Metadata usage

1. **Store and display only** — Store section headings on chunks, use them in context formatting (`[Source: file > section]`) so the LLM sees document structure. Pros: cheap, no query-time overhead. Cons: doesn't actively filter retrieval.

2. **Active query-time filtering** — Use section headings to filter or boost results at search time. Pros: more precise retrieval. Cons: requires either an LLM pre-processing step to extract expected section names or a second embedding comparison; both add latency and complexity for uncertain gain.

## Decision

- **Chunking**: Option 2 — Markdown-aware chunking. For `.md` files, split on `#`, `##`, `###` headers first, then sub-split oversized sections at 1000 chars with 200-char overlap. For PDF and TXT, use `RecursiveCharacterTextSplitter` with the new 1000/200 defaults. Store the concatenated header path (e.g. `"Damage > Receiving damage"`) as `section_heading` on each chunk (nullable — non-Markdown files have no heading).
- **Chunk size defaults**: Raise from 500/100 to 1000/200. This keeps chunks within `all-MiniLM-L6-v2`'s effective 256-token (~1200 char) input window while roughly doubling context per chunk.
- **Deduplication**: Option 2 — Post-retrieval dedup. Over-fetch 2x candidates (`RETRIEVAL_CANDIDATE_K=10`), then merge adjacent same-document chunks and drop chunks with >70% Jaccard token overlap. Final result limited to `RETRIEVAL_TOP_K=5`.
- **Metadata**: Option 1 — Store and display. Section headings appear in the `[Source: ...]` line passed to the LLM. Active filtering skipped for now.
- **Skip**: Parent-child retrieval (option 3 chunking) and cross-encoder reranking (option 3 dedup) are deferred. Both add significant complexity for diminishing returns once chunking is fixed. They can be revisited if retrieval quality is still insufficient after these changes.

## Consequences

- **Schema migration required**: New nullable `section_heading` column on `chunks`. Existing chunks have `NULL` headings and should be re-processed.
- **Re-seed needed**: Existing documents must be re-processed with the new chunking strategy. Simplest path: truncate and re-run `scripts/seed_wiki.py`.
- **Non-Markdown files unaffected structurally**: PDFs and TXT files get larger chunks but no section metadata. This is acceptable since the primary content source is Markdown wiki pages.
- **Over-fetch increases query cost slightly**: Retrieving 10 candidates instead of 5 is negligible for pgvector with the current corpus size.
- **No new dependencies**: `MarkdownHeaderTextSplitter` is already available from `langchain-text-splitters>=0.3`.
