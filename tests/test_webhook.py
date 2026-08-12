import hashlib
import hmac

from app.api.webhook import verify_signature


def test_verify_signature_accepts_valid_sha256_signature() -> None:
    body = b'{"action":"opened"}'
    secret = "secret"
    signature = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

    assert verify_signature(secret, body, signature)


def test_verify_signature_rejects_invalid_signature() -> None:
    assert not verify_signature("secret", b"{}", "sha256=bad")


def test_verify_signature_rejects_missing_secret() -> None:
    assert not verify_signature("", b"{}", "sha256=bad")
