"""AWS Lambda entry point — Mangum adapter for FastAPI."""

from mangum import Mangum

from app.main import app

handler = Mangum(app, lifespan="auto")
