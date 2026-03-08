import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".pdf", ".txt", ".md"})

EXTENSION_TO_CONTENT_TYPE: dict[str, str] = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
    ".md": "text/markdown",
}


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
    allowed_extensions: frozenset[str] = field(default_factory=lambda: ALLOWED_EXTENSIONS)
    embedding_model: str = field(
        default_factory=lambda: os.environ.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    )
    llm_provider: str = field(default_factory=lambda: os.environ.get("LLM_PROVIDER", "mock"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("OLLAMA_MODEL", "llama3"))
    ollama_base_url: str = field(
        default_factory=lambda: os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    similarity_threshold: float = field(
        default_factory=lambda: float(os.environ.get("SIMILARITY_THRESHOLD", "0.3"))
    )
    retrieval_top_k: int = field(
        default_factory=lambda: int(os.environ.get("RETRIEVAL_TOP_K", "5"))
    )
    retrieval_candidate_k: int = field(
        default_factory=lambda: int(os.environ.get("RETRIEVAL_CANDIDATE_K", "20"))
    )
    retrieval_mode: str = field(default_factory=lambda: os.environ.get("RETRIEVAL_MODE", "hybrid"))
    max_upload_bytes: int = field(
        default_factory=lambda: int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024)))
    )
    max_history_messages: int = field(
        default_factory=lambda: int(os.environ.get("MAX_HISTORY_MESSAGES", "50"))
    )
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
