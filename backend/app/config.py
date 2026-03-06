import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".txt", ".md"})


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://notebooklm:notebooklm@localhost:5432/notebooklm",
        )
    )
    upload_dir: Path = field(
        default_factory=lambda: Path(os.environ.get("UPLOAD_DIR", "data/uploads"))
    )
    allowed_extensions: frozenset[str] = field(
        default_factory=lambda: ALLOWED_EXTENSIONS
    )
    embedding_model: str = field(
        default_factory=lambda: os.environ.get(
            "EMBEDDING_MODEL", "all-MiniLM-L6-v2"
        )
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
