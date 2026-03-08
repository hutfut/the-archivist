# ADR-0007: Frontend Routing and Page Architecture

**Date:** 2026-03-08
**Status:** Accepted

## Context

The existing frontend is a single-page layout with a sidebar (documents) and main area (chat). To support dedicated pages for document browsing, individual document viewing, search results, and chat, we need client-side routing with distinct URL-addressable pages.

## Options Considered

1. **React Router v7** -- The de-facto standard for React SPAs. Stable, well-documented, supports nested layouts and code splitting via lazy routes.
2. **TanStack Router** -- Type-safe routing with built-in search param validation. Newer, smaller community, adds learning curve.
3. **Next.js / Remix** -- Full-stack frameworks with file-based routing. Over-engineering for a Vite-based SPA that already has a separate FastAPI backend.

## Decision

Use **React Router v7** with a nested layout pattern:

- `Layout` component wraps all routes with header, footer, and chat drawer
- Routes: `/` (home/library), `/doc/:slug` (document view), `/search` (results), `/chat` (full chat)
- Slug format: `{uuid}--{kebab-title}` to embed the document ID while keeping URLs readable
- No code splitting initially -- the app is small enough that a single bundle is acceptable

## Consequences

- **Positive:** URL-addressable pages, browser back/forward work naturally, bookmarkable search results and document views
- **Positive:** Nested layout avoids re-mounting shared state (chat, document list) on navigation
- **Negative:** Adds ~15KB to bundle (acceptable for the routing capabilities gained)
- **Risk:** Existing chat state must be lifted from the page level to the layout level to persist across navigation
