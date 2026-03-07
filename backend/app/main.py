import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s  %(name)s: %(message)s",
)

from app.agent.graph import build_agent_graph
from app.agent.llm import create_llm
from app.api.conversations import init_agent
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.config import get_settings
from app.db.session import close_db, get_session_factory, init_db
from app.services.embedding import HuggingFaceEmbeddingService
from app.services.processing import init_processor
from app.services.retrieval import RetrievalService


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    settings = get_settings()
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    await init_db(settings.database_url)

    embedding_service = HuggingFaceEmbeddingService(settings.embedding_model)
    init_processor(embedding_service)

    retrieval_service = RetrievalService(
        embedding_service, retrieval_mode=settings.retrieval_mode,
    )
    llm = create_llm(settings)
    agent_graph = build_agent_graph(
        retrieval_service=retrieval_service,
        llm=llm,
        session_factory=get_session_factory(),
        similarity_threshold=settings.similarity_threshold,
        top_k=settings.retrieval_top_k,
        candidate_k=settings.retrieval_candidate_k,
        query_rewrite=settings.llm_provider != "mock",
    )
    init_agent(agent_graph)

    yield
    await close_db()


def create_app() -> FastAPI:
    app = FastAPI(title="NotebookLM", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(conversations_router)

    return app


app = create_app()
