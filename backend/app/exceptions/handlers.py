"""Global exception handlers for FastAPI."""

import structlog
from fastapi import Request
from fastapi.responses import JSONResponse

from app.exceptions.custom import EMIPException

logger = structlog.get_logger(__name__)


async def emip_exception_handler(request: Request, exc: EMIPException) -> JSONResponse:
    """Handle EMIP custom exceptions."""
    logger.warning(
        "EMIP exception",
        exception_type=type(exc).__name__,
        message=exc.message,
        status_code=exc.status_code,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    logger.error(
        "Unhandled exception",
        exception_type=type(exc).__name__,
        message=str(exc),
        path=request.url.path,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
