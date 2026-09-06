from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from app.core.config import get_settings

settings = get_settings()


class TokenError(Exception):
    """Raised by decode_access_token with a machine-readable `reason` so
    callers can log a precise diagnostic without needing to inspect the
    token or secret. The client-facing message stays generic either way —
    this is for server-side diagnostics only."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(subject: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except ExpiredSignatureError as exc:
        raise TokenError("expired") from exc
    except JWTClaimsError as exc:
        raise TokenError("invalid_claims") from exc
    except JWTError as exc:
        # Covers bad signature (wrong secret/algorithm) and malformed tokens.
        raise TokenError("invalid_signature_or_malformed") from exc


def unverified_claims(token: str) -> dict | None:
    """Best-effort peek at a token's claims WITHOUT verifying the signature —
    diagnostics only (dev-mode logging), never used for authorization."""
    try:
        return jwt.get_unverified_claims(token)
    except JWTError:
        return None
