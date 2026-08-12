from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["ui"])
STATIC_DIR = Path(__file__).parent / "static"


@router.get("/", include_in_schema=False)
def ui_index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")
