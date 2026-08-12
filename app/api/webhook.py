import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.metrics import WEBHOOK_EVENTS
from app.workers.tasks import review_pull_request

router = APIRouter(prefix="/api/github", tags=["github"])
logger = logging.getLogger(__name__)

SUPPORTED_ACTIONS = {"opened", "reopened", "synchronize", "ready_for_review"}


class WebhookAccepted(BaseModel):
    accepted: bool
    job_id: str | None = None


def verify_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not secret:
        logger.warning("webhook secret is empty; rejecting webhook")
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@router.post("/webhook", response_model=WebhookAccepted, status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(default=""),
    x_hub_signature_256: str | None = Header(default=None),
) -> WebhookAccepted:
    settings = get_settings()
    body = await request.body()
    if not verify_signature(settings.github_webhook_secret, body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    payload: dict[str, Any] = await request.json()
    action = str(payload.get("action", ""))
    WEBHOOK_EVENTS.labels(event=x_github_event, action=action).inc()

    if x_github_event != "pull_request" or action not in SUPPORTED_ACTIONS:
        return WebhookAccepted(accepted=False)

    pull_request = payload.get("pull_request") or {}
    repository = payload.get("repository") or {}
    installation = payload.get("installation") or {}
    required = [pull_request.get("number"), repository.get("full_name"), installation.get("id")]
    if any(value is None for value in required):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing PR fields")

    job_payload = {
        "repository_full_name": repository["full_name"],
        "pull_request_number": pull_request["number"],
        "installation_id": installation["id"],
        "head_sha": pull_request.get("head", {}).get("sha", ""),
        "payload": payload,
    }
    result = review_pull_request.delay(job_payload)
    return WebhookAccepted(accepted=True, job_id=result.id)
