"""FastAPI application entry point — enterprise-grade configuration."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.dependencies import get_aws_clients
from app.core.security import APIKeyMiddleware
from app.core.settings import get_settings
from app.core.startup import on_shutdown, on_startup
from app.exceptions.custom import EMIPException
from app.exceptions.handlers import emip_exception_handler, generic_exception_handler
from app.monitoring.logging import configure_structured_logging
from app.monitoring.middleware import CorrelationMiddleware
from app.routes import analyze, codegen, deploy, jobs, results, upload

settings = get_settings()

configure_structured_logging(log_level=settings.log_level)

app = FastAPI(
    title=settings.app_name,
    description="AI-driven monolith-to-microservices migration analysis",
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_exception_handler(EMIPException, emip_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Correlation-ID"],
)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(APIKeyMiddleware)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(deploy.router, prefix="/api", tags=["deploy"])
app.include_router(codegen.router, prefix="/api", tags=["codegen"])
app.include_router(results.router, prefix="/api", tags=["results"])
app.include_router(jobs.router, prefix="/api", tags=["jobs"])


@app.get("/health", tags=["health"])
async def health_check():
    return {"status": "healthy", "version": settings.app_version}


@app.get("/api/health", tags=["health"])
async def api_health():
    aws_connected = False
    try:
        clients = get_aws_clients()
        clients.sts.get_caller_identity()
        aws_connected = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": settings.app_version,
        "aws_connected": aws_connected,
        "environment": settings.environment,
    }


@app.on_event("startup")
async def startup_event():
    on_startup()


@app.on_event("shutdown")
async def shutdown_event():
    on_shutdown()
