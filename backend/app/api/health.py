import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
async def health_check(
    session: AsyncSession = Depends(get_session),
) -> JSONResponse:
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse(content={"status": "ok"})
    except Exception:
        logger.exception("Health check failed: database unreachable")
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "detail": "Database connection failed"},
        )
