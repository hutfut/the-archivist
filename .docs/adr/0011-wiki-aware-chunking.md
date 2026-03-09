# 11. Wiki-aware chunking

**Date**: 2026-03-08  
**Status**: Accepted

## Context

RAG retrieval on wiki-style content suffers from vector noise: chunks mix unrelated blocks (lists, historical vs current, sub-topics) when splitting is driven only by character limits. Structural boundaries (headings, horizontal rules) are often ignored, so a single chunk can span multiple logical sections and degrade retrieval relevance.

## Options considered

1. **Extend header hierarchy only** — Add `####` (h4) so more sections are bounded by headings; keep existing 1000/200 chunk size. Pros: minimal change. Cons: oversized sections still sub-split at 1000 chars, leaving large mixed-context chunks.

2. **Extended headers + smaller markdown chunk size (chosen)** — Add `####` and use markdown-specific limits (700 chars, 140 overlap) only for `chunk_markdown`; keep 1000/200 for plain text/PDF via `chunk_text`. Pros: sections align with headings; when sub-splitting is needed, smaller chunks reduce mixed-context. Cons: more chunks per document for markdown.

3. **Horizontal rules as hard boundaries** — Treat standalone `---`, `***`, `___` as split points so major wiki blocks become separate chunks. Deferred: can be implemented as an optional second step (pre-split on HR, then run header split on each block). Bold-line or list-aware separators also deferred.

4. **List-aware or custom separators** — Split on list boundaries or other wiki conventions. Deferred: more complex and corpus-specific; header + size cover the main structural cases.

## Decision

- **Headers**: Extend `_MARKDOWN_HEADERS` with `("####", "h4")`. `_build_heading_path` includes h4 so `section_heading` can be e.g. `"Top > Middle > Deep > Deeper"`. Backward-compatible (deeper path only).
- **Markdown chunk size**: Introduce `MARKDOWN_CHUNK_SIZE = 700` and `MARKDOWN_CHUNK_OVERLAP = 140`; use them as defaults only in `chunk_markdown`. `DEFAULT_CHUNK_SIZE` / `DEFAULT_CHUNK_OVERLAP` (1000/200) remain for `chunk_text` and non-markdown pipeline path.

## Consequences

- No schema change; `section_heading` may contain longer paths (h4). Existing documents should be re-processed (re-upload or re-run seed) to re-chunk and re-embed.
- No new runtime dependencies; LangChain text splitters only.
- Plain text and PDF pipeline unchanged: still 1000/200 via `chunk_text`.
