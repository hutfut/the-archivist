import contextvars
import logging
import os
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")


class _RequestIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get("")  # type: ignore[attr-defined]
        return True


logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(levelname)s  [request_id=%(request_id)s] %(name)s: %(message)s",
)
for _handler in logging.getLogger().handlers:
    _handler.addFilter(_RequestIDFilter())

from app.agent.graph import build_agent_graph
from app.agent.llm import create_llm
from app.api.conversations import init_agent
from app.api.conversations import router as conversations_router
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.search import init_search
from app.api.search import router as search_router
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
        embedding_service,
        retrieval_mode=settings.retrieval_mode,
    )
    init_search(retrieval_service)

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


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rid = str(uuid.uuid4())
        request_id_ctx.set(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response


FIELD_LABELS: dict[str, str] = {
    "content": "Message content",
    "file": "File",
}


def _format_validation_error(exc: RequestValidationError) -> str:
    """Translate Pydantic validation errors into plain-English messages."""
    messages: list[str] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        field = str(loc[-1]) if loc else "input"
        label = FIELD_LABELS.get(field, field.replace("_", " ").capitalize())
        err_type = err.get("type", "")
        if err_type == "missing":
            messages.append(f"{label} is required.")
        elif err_type == "string_too_short":
            messages.append(f"{label} must not be empty.")
        elif err_type == "string_too_long":
            ctx = err.get("ctx", {})
            max_length = ctx.get("max_length", "?")
            messages.append(f"{label} must be at most {max_length} characters.")
        elif err_type == "uuid_parsing":
            messages.append(f"'{field}' is not a valid ID.")
        else:
            messages.append(err.get("msg", "Validation error."))
    return " ".join(messages) if messages else "Invalid request."


def create_app() -> FastAPI:
    app = FastAPI(title="NotebookLM", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": _format_validation_error(exc)},
        )

    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(conversations_router)

    return app


app = create_app()
