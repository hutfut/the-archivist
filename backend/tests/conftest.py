from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer

from sqlalchemy import text

from app.agent.graph import build_agent_graph
from app.agent.llm import MockChatModel
from app.api.conversations import get_agent, init_agent
from app.api.search import get_retrieval_service, init_search
from app.config import Settings, get_settings
from app.db.models import Base
from app.db.session import close_db, get_session_factory, init_db
from app.main import create_app
from app.services.embedding import MockEmbeddingService
from app.services.processing import get_processor, init_processor
from app.services.retrieval import RetrievalService


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer(
        image="pgvector/pgvector:pg17",
        username="test",
        password="test",
        dbname="test",
    ) as pg:
        yield pg


@pytest.fixture(scope="session")
def database_url(pg_container: PostgresContainer) -> str:
    host = pg_container.get_container_host_ip()
    port = pg_container.get_exposed_port(5432)
    return f"postgresql+asyncpg://test:test@{host}:{port}/test"


@pytest.fixture
async def test_settings(tmp_path: Path, database_url: str) -> Settings:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return Settings(
        database_url=database_url,
        upload_dir=upload_dir,
        max_upload_bytes=1024 * 1024,
    )


async def _create_schema(database_url: str) -> None:
    """Create pgvector extension and all tables for tests.

    Production relies on Alembic migrations; tests use create_all for speed.
    """
    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    await init_db(test_settings.database_url)
    await _create_schema(test_settings.database_url)

    mock_embeddings = MockEmbeddingService()
    init_processor(mock_embeddings)

    retrieval_service = RetrievalService(mock_embeddings, retrieval_mode="vector")
    init_search(retrieval_service)
    mock_llm = MockChatModel()
    agent_graph = build_agent_graph(
        retrieval_service=retrieval_service,
        llm=mock_llm,
        session_factory=get_session_factory(),
        similarity_threshold=-1.0,
        top_k=5,
        candidate_k=10,
    )
    init_agent(agent_graph)

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_processor] = lambda: get_processor()
    app.dependency_overrides[get_agent] = lambda: agent_graph
    app.dependency_overrides[get_retrieval_service] = lambda: retrieval_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await close_db()

    engine = create_async_engine(test_settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
