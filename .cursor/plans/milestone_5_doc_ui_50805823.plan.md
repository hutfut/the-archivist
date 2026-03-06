---
name: Milestone 5 Doc UI
overview: Add Tailwind CSS v4 to the frontend, build a typed API client for document endpoints, and implement the document management UI (upload with drag-and-drop, list with metadata, delete with confirmation dialog) -- all wired into the existing two-panel layout.
todos:
  - id: m5-tailwind
    content: Install Tailwind CSS v4, configure Vite plugin, migrate existing layout styles to Tailwind
    status: completed
  - id: m5-api-client
    content: Create typed API client (fetchDocuments, uploadDocument, deleteDocument) and ApiError class
    status: completed
  - id: m5-components
    content: Build DocumentUpload, DocumentList, ConfirmDialog components + useDocuments hook, wire into App
    status: completed
  - id: m5-self-review
    content: Self-review against code-review checklist, verify build, test against running backend, commit
    status: completed
isProject: false
---

# Milestone 5: Frontend Document Management

## Current State

- Milestones 1-4 complete: backend has document CRUD (`POST/GET/DELETE /api/documents`) and chat API
- Frontend is a bare Vite + React 19 + TypeScript scaffold with placeholder content
- Two-panel layout exists in [frontend/src/App.tsx](frontend/src/App.tsx) (documents panel left, chat panel right)
- Plain CSS in [frontend/src/App.css](frontend/src/App.css) and [frontend/src/index.css](frontend/src/index.css)
- No `components/`, `api/`, or `hooks/` directories yet
- Vite proxy to backend at `localhost:8000` already configured

## Backend API Contract (what we're building against)

- `POST /api/documents` -- multipart `file` field -> `DocumentResponse` (201)
- `GET /api/documents` -> `{ documents: DocumentResponse[] }`
- `DELETE /api/documents/{id}` -> 204 (no body)
- Allowed extensions: `.pdf`, `.txt`, `.md`
- Error shape: `{ detail: string }`

```typescript
interface DocumentResponse {
  id: string;
  filename: string;
  content_type: string;
  file_size: number;
  chunk_count: number;
  created_at: string; // ISO 8601
}
```

## Step 1: Add Tailwind CSS v4

Tailwind v4 with the `@tailwindcss/vite` plugin -- no PostCSS config or `tailwind.config.js` needed.

- Install: `npm install tailwindcss @tailwindcss/vite`
- Add `tailwindcss()` plugin to [frontend/vite.config.ts](frontend/vite.config.ts)
- Replace [frontend/src/index.css](frontend/src/index.css) with `@import "tailwindcss";` plus custom theme (fonts, dark mode)
- Migrate [frontend/src/App.tsx](frontend/src/App.tsx) layout to Tailwind utility classes
- Remove [frontend/src/App.css](frontend/src/App.css) (styles replaced by Tailwind classes inline)
- Verify the app builds and the two-panel layout renders correctly

## Step 2: API Client and Types

Create the API layer with typed functions using native `fetch` (no new deps).

**New files:**

- `frontend/src/api/documents.ts` -- `fetchDocuments()`, `uploadDocument(file)`, `deleteDocument(id)`
- `frontend/src/api/errors.ts` -- `ApiError` class wrapping status code and message, with helper to extract the `detail` field from backend error responses

Type definitions live alongside the API functions (co-located, not a separate types file) to keep things simple.

## Step 3: Document Management Components and Hook

**New files:**

- `frontend/src/hooks/useDocuments.ts` -- custom hook encapsulating document state:
  - `documents`, `loading`, `error` state
  - `upload(file)`, `remove(id)` actions that call the API client and optimistically update state
  - Auto-fetches on mount via `useEffect`
- `frontend/src/components/DocumentUpload.tsx` -- drag-and-drop zone + click-to-browse
  - Hidden `<input type="file" accept=".pdf,.txt,.md">` triggered by click
  - Visual drag-over state (border highlight)
  - Shows loading spinner/bar during upload+processing
  - Client-side validation: file extension check, empty file check
  - Displays error messages inline
- `frontend/src/components/DocumentList.tsx` -- renders the list of documents
  - Each item shows: filename, formatted file size (e.g., "2.3 MB"), chunk count, upload date
  - Delete button per document
  - Empty state: "No documents uploaded yet. Upload a document to get started."
- `frontend/src/components/ConfirmDialog.tsx` -- reusable confirmation modal
  - Used for delete confirmation: "Delete {filename}? This cannot be undone."
  - Accept/Cancel buttons
  - Built with native `<dialog>` element for accessibility

**Modified files:**

- `frontend/src/App.tsx` -- replace the documents panel placeholder with `DocumentPanel` composed of `DocumentUpload` + `DocumentList`, wire up `useDocuments` hook

## Component Tree

```
App
 +-- aside.documents-panel
 |    +-- DocumentUpload (drag-drop zone, file input, loading state)
 |    +-- DocumentList (list items with delete buttons)
 |    +-- ConfirmDialog (modal, shown on delete click)
 +-- main.chat-panel
      +-- (placeholder for M6)
```

## Key Design Decisions

- **Native `fetch**` over axios/ky -- keeps deps minimal; the API surface is small (3 endpoints)
- `**useDocuments` hook** -- single source of truth for document state; keeps components presentational
- **Client-side validation mirrors backend** -- catch obvious errors (wrong extension, empty file) before making the request
- **Native `<dialog>` for confirmation** -- accessible by default, no modal library needed
- **No file size progress tracking** -- `fetch` doesn't support upload progress events; a simple loading state (spinner + "Uploading...") is shown during the entire upload+process request
- **Tailwind v4** -- user preference; modern utility-first CSS with Vite plugin, no config file needed

## Commit Plan

1. `chore(frontend): add Tailwind CSS v4 and migrate layout` -- install, configure, migrate App layout
2. `feat(frontend): add document API client` -- api/documents.ts, api/errors.ts
3. `feat(frontend): add document upload, list, and delete UI` -- components, hook, App integration

