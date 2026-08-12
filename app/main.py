from fastapi import FastAPI, Response
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.api.dashboard import router as dashboard_router
from app.api.webhook import router as github_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.ui.routes import STATIC_DIR
from app.ui.routes import router as ui_router

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title="GitHub Pull Request Review Agent", version="0.1.0")
app.include_router(github_router)
app.include_router(dashboard_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.include_router(ui_router)


@app.get("/api/info")
def api_info() -> dict[str, str]:
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
