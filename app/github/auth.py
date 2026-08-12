from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import Settings


def build_app_jwt(settings: Settings) -> str:
    now = datetime.now(UTC)
    payload = {
        "iat": int((now - timedelta(seconds=60)).timestamp()),
        "exp": int((now + timedelta(minutes=9)).timestamp()),
        "iss": settings.github_app_id,
    }
    return jwt.encode(payload, settings.github_private_key, algorithm="RS256")
