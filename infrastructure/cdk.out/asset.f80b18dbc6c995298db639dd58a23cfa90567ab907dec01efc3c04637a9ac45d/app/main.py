import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.routes import upload, analyze, deploy, results

load_dotenv()

app = FastAPI(
    title="Enterprise Modernization Intelligence Platform",
    description="AI-driven monolith-to-microservices migration analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_URL", "http://localhost:5173"),
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api", tags=["upload"])
app.include_router(analyze.router, prefix="/api", tags=["analyze"])
app.include_router(deploy.router, prefix="/api", tags=["deploy"])
app.include_router(results.router, prefix="/api", tags=["results"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/health")
async def api_health():
    aws_connected = False
    try:
        import boto3
        sts = boto3.client("sts")
        sts.get_caller_identity()
        aws_connected = True
    except Exception:
        pass

    return {
        "status": "healthy",
        "version": "1.0.0",
        "aws_connected": aws_connected,
    }
