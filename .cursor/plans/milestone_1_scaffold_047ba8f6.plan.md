---
name: Milestone 1 Scaffold
overview: Scaffold the backend (Python/FastAPI with health check and tests) and frontend (Vite/React/TypeScript with proxy config), so both servers run, communicate, and have passing tests.
todos:
  - id: m1-backend
    content: Create backend/ with FastAPI, health endpoint, pyproject.toml, directory structure, and passing pytest
    status: pending
  - id: m1-frontend
    content: Create frontend/ with Vite+React+TS, two-panel layout placeholder, proxy config, and successful build
    status: pending
  - id: m1-verify
    content: Verify both servers run, proxy works, all tests pass, then commit
    status: pending
isProject: false
---

# Milestone 1: Project Scaffold

## What we're building

Both servers running, communicating via proxy, with passing tests. Per the [implementation plan](.cursor/plans/notebooklm_implementation_plan_c45168f4.plan.md) Milestone 1 spec.

## Current state

- Project root has: `.gitignore`, `AGENTS.md`, `.docs/` (with ADR 0001 and PROMPT.md), `.cursor/` rules and plans
- Python 3.12.3, Node 20.19.5, npm 10.8.2 available
- `python3 -m venv` works with pip included
- No `backend/` or `frontend/` directories yet

## Step 1: Backend scaffold

Create `backend/` with:

- `**backend/pyproject.toml**` -- project metadata and dependencies (fastapi, uvicorn, pydantic, pytest, httpx, python-multipart). Pin only major versions for flexibility.
- `**backend/app/__init__.py**` -- empty
- `**backend/app/main.py**` -- FastAPI app factory with CORS middleware, mounts `/api` routes
- `**backend/app/api/__init__.py**` -- empty
- `**backend/app/api/health.py**` -- `GET /api/health` returning `{"status": "ok"}`
- Stub directories with `__init__.py`: `app/models/`, `app/services/`, `app/agent/`, `app/db/`
- `**backend/tests/__init__.py**` -- empty
- `**backend/tests/conftest.py**` -- httpx `AsyncClient` fixture for FastAPI test client
- `**backend/tests/test_health.py**` -- test that `GET /api/health` returns 200 and expected JSON

Setup: `python3 -m venv backend/.venv && source backend/.venv/bin/activate && pip install -e ".[dev]"`

Verify: `cd backend && pytest` passes

**Commit**: `feat(backend): scaffold FastAPI project with health endpoint and tests`

## Step 2: Frontend scaffold

Create `frontend/` via `npm create vite@latest frontend -- --template react-ts`:

- Clean up boilerplate (remove default Vite counter app)
- `**frontend/src/App.tsx**` -- minimal two-panel layout placeholder (document panel + chat panel)
- `**frontend/src/App.css**` -- basic two-column layout styles
- `**frontend/vite.config.ts**` -- add proxy config for `/api` to `http://localhost:8000`

Verify: `cd frontend && npm install && npm run build` succeeds

**Commit**: `feat(frontend): scaffold Vite React TypeScript app with proxy config`

## Step 3: Integration verification

- Start backend: `cd backend && uvicorn app.main:app --reload`
- Start frontend: `cd frontend && npm run dev`
- Frontend's proxy forwards `/api/health` to backend correctly
- All tests pass, both servers start cleanly

**Commit** (if any proxy/integration tweaks needed): `chore: verify frontend-backend proxy integration`

## Key decisions

- Use `pyproject.toml` (PEP 621) rather than `requirements.txt` -- modern Python packaging, supports dev extras
- CORS configured to allow `localhost:5173` (Vite default) for development
- FastAPI app uses a simple module-level app instance (no factory pattern needed for this scale)
- Keep frontend styling minimal -- just enough layout to show the two-panel structure

