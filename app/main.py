from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.webhook import router as github_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="GitHub Pull Request Review Agent", version="0.1.0")
app.include_router(github_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "GitHub Pull Request Review Agent",
        "status": "running",
        "health": "/api/healthz",
        "webhook": "/api/github/webhook",
    }


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/healthz")
def api_healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/metrics")
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
