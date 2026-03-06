# 2. Data Storage Strategy

**Date**: 2026-03-06  
**Status**: Accepted

## Context

The application needs to persist three categories of data:

1. **Structured metadata** — document records (filename, size, timestamps), conversations, and messages.
2. **Raw files** — the original uploaded documents (PDF, TXT, Markdown).
3. **Vector embeddings** — chunked document text with dense vector representations for semantic retrieval.

We need a storage strategy that uses production-like patterns, supports async access from FastAPI, and would translate directly to a real deployment.

## Options considered

1. **SQLite + filesystem + ChromaDB** — Zero-config for metadata (SQLite), filesystem for files, ChromaDB for vectors. Simple local setup but SQLite lacks concurrent write support, JSON operators, and proper type system. ChromaDB adds a separate storage layer with its own API. Not representative of production deployments.

2. **SQLAlchemy async (SQLite) + filesystem + ChromaDB** — Adds an ORM layer over option 1. Better patterns but still two separate storage systems for structured and vector data, and SQLite limitations remain.

3. **PostgreSQL + filesystem + pgvector** — Production-grade relational database with native vector search via the pgvector extension. SQLAlchemy async with `asyncpg` driver. Single database for both structured metadata and vector embeddings. Requires running a PostgreSQL container, but this is trivial with Docker Compose. Matches real-world deployments where PostgreSQL + pgvector (or a managed equivalent) is standard.

4. **PostgreSQL + S3/MinIO + pgvector** — Full production stack with object storage for files. Adds operational complexity (another service to run) without meaningful benefit for a local demo. Filesystem is a reasonable stand-in for object storage.

## Decision

**PostgreSQL with pgvector** for structured metadata and vector embeddings, **local filesystem** for raw uploaded files, accessed through **SQLAlchemy 2.0 async** with the `asyncpg` driver.

PostgreSQL is the standard production database for Python web services. The pgvector extension adds vector similarity search as a native column type, eliminating the need for a separate vector store. This means document metadata, chat history, and vector embeddings all live in one database with one connection pool, one transaction boundary, and one backup strategy.

SQLAlchemy 2.0 async with `Mapped` type annotations, `async_sessionmaker`, and `AsyncSession` provides the same ORM patterns used in production FastAPI services. The `asyncpg` driver gives high-performance async PostgreSQL access.

Files are stored on the filesystem at `data/uploads/{document_id}/{filename}` rather than as blobs in the database. This mirrors how production systems use object storage separate from their relational store.

PostgreSQL runs in a Docker container via Docker Compose alongside the backend and frontend, making the full stack launchable with a single command.

## Consequences

- **Requires Docker**: PostgreSQL runs in a container. `docker compose up` starts everything. This is a minimal ask for a production-like setup.
- **Alembic for migrations**: Schema changes are managed through Alembic migration scripts, matching production workflows. Migrations run automatically on container startup (`alembic upgrade head` in the entrypoint) and can be run manually during development. Tests use `Base.metadata.create_all()` directly for speed.
- **Single database for structured + vector data**: Simplifies operations (one backup, one connection pool) but couples the vector store to PostgreSQL. In a real system this trade-off is usually acceptable; pgvector performance is sufficient up to millions of vectors.
- **Tests use SQLite**: Unit tests use SQLite via aiosqlite for speed and isolation (no running database required). Integration tests against PostgreSQL can be added if needed. SQLAlchemy abstracts the differences for standard queries.
- **Portable ORM layer**: Swapping PostgreSQL for another database requires only a connection URL change — the SQLAlchemy models and session management remain identical.
