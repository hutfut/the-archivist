from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import Settings, get_settings
from app.db.session import close_db, get_session, init_db
from app.main import create_app


@pytest.fixture
async def test_settings(tmp_path: Path) -> Settings:
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    return Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        upload_dir=upload_dir,
    )


@pytest.fixture
async def client(test_settings: Settings) -> AsyncGenerator[AsyncClient, None]:
    await init_db(test_settings.database_url)

    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await close_db()
