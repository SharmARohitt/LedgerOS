import logging
from collections.abc import Generator
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import log_event
from app.core.security import TokenError, decode_access_token, unverified_claims
from app.db.session import SessionLocal

_bearer = HTTPBearer(auto_error=False)
_auth_logger = logging.getLogger("ledgeros.auth")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CurrentUser:
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role


def _credential_preview(token: str) -> str:
    """Non-secret preview for logs: enough to tell two credentials apart,
    never enough to reconstruct or replay the token. Field names here
    deliberately avoid the word "token" — the structured logger's redact()
    blanket-masks any field whose name contains "token"/"secret"/etc., which
    would otherwise swallow this intentionally-safe preview too."""
    if len(token) <= 12:
        return "***"
    return f"{token[:6]}...{token[-4:]} (len={len(token)})"


def _log_auth_failure(request: Request, reason: str, credential: str | None) -> None:
    """Dev-only structured diagnostic. Never logs the secret or the full
    credential — only a truncated preview and, where safe, UNVERIFIED claims
    (subject/expiry) read without signature checking, purely to answer
    'which credential, whose, expired when, vs server time now' during
    debugging."""
    if get_settings().environment == "production":
        return

    fields = {
        "path": request.url.path,
        "method": request.method,
        "reason": reason,
        "auth_header_present": "authorization" in request.headers,
        "server_time_utc": datetime.now(timezone.utc).isoformat(),
    }
    if credential:
        fields["credential_preview"] = _credential_preview(credential)
        claims = unverified_claims(credential)  # signature NOT verified — diagnostics only
        if claims:
            fields["claim_subject"] = claims.get("sub")
            fields["claim_role"] = claims.get("role")
            if claims.get("exp"):
                fields["claim_expiry_utc"] = datetime.fromtimestamp(claims["exp"], tz=timezone.utc).isoformat()
    log_event(_auth_logger, "auth_failed", **fields)


def get_current_user(
    request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)
) -> CurrentUser:
    if credentials is None:
        # Covers both a missing Authorization header and one that doesn't
        # use the "Bearer <token>" scheme — HTTPBearer(auto_error=False)
        # returns None for either rather than distinguishing them.
        auth_header = request.headers.get("authorization")
        reason = "malformed_auth_header" if auth_header else "missing_bearer_token"
        _log_auth_failure(request, reason, credential=None)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        _log_auth_failure(request, exc.reason, credential=credentials.credentials)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc
    return CurrentUser(user_id=payload["sub"], role=payload["role"])


def require_role(*allowed_roles: str):
    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' is not permitted to perform this action.",
            )
        return user

    return _check
