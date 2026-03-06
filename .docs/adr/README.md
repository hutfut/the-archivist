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

When you add an ADR, append a row to this table.
