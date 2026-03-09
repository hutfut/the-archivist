# Architecture Decision Records (ADR)

Significant architectural and technical decisions are recorded here as **one document per decision**, following the [ADR](https://adr.github.io/) convention.

## Adding a new ADR

1. **Number**: Use the next sequential number, zero-padded to 4 digits (e.g. `0001`, `0002`).
2. **Filename**: `NNNN-short-title-with-dashes.md` (e.g. `0001-use-python-and-fastapi.md`).
3. **Content**: Use the template below in the new file.

## Template

```markdown
# N. [Title]

**Date**: YYYY-MM-DD  
**Status**: Accepted (or Proposed / Deprecated / Superseded by NNNN)

## Context

What problem or question prompted this decision?

## Options considered

1. **Option A** — pros / cons
2. **Option B** — pros / cons

## Decision

Which option was chosen and why.

## Consequences

Trade-offs accepted, follow-on work, risks.
```

## Index

| #   | Title | Date |
|-----|-------|------|
| 0001 | [Use Python with FastAPI, React, and LangChain/LangGraph](0001-use-python-fastapi-react.md) | 2026-03-06 |
| 0002 | [Data Storage Strategy](0002-data-storage-strategy.md) | 2026-03-06 |
| 0003 | [Document Processing and Embedding Approach](0003-document-processing-and-embedding.md) | 2026-03-06 |
| 0004 | [LangGraph Agent Architecture](0004-langgraph-agent-architecture.md) | 2026-03-06 |
| 0005 | [RAG Retrieval Quality Improvements](0005-rag-retrieval-improvements.md) | 2026-03-07 |
| 0006 | [Hybrid Search and Retrieval Quality](0006-hybrid-search-and-retrieval-quality.md) | 2026-03-07 |
| 0007 | [Frontend Routing and Page Architecture](0007-frontend-routing-and-page-architecture.md) | 2026-03-08 |
| 0008 | [PoE2 Design System Approach](0008-poe2-design-system-approach.md) | 2026-03-08 |
| 0009 | [Frontend Test Framework Choice](0009-frontend-test-framework.md) | 2026-03-08 |
| 0010 | [Anthropic LLM Integration](0010-anthropic-llm-integration.md) | 2026-03-08 |
| 0011 | [Wiki-aware chunking](0011-wiki-aware-chunking.md) | 2026-03-08 |

When you add an ADR, append a row to this table.
