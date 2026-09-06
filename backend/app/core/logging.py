import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")

_REDACT_KEYS = {"password", "secret", "token", "api_key", "authorization", "webhook_secret"}


def redact(payload: dict) -> dict:
    out = {}
    for k, v in payload.items():
        if any(rk in k.lower() for rk in _REDACT_KEYS):
            out[k] = "***REDACTED***"
        elif isinstance(v, dict):
            out[k] = redact(v)
        else:
            out[k] = v
    return out


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if hasattr(record, "extra_fields"):
            payload.update(redact(record.extra_fields))
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)


def new_request_id() -> str:
    return uuid.uuid4().hex[:16]


def log_event(logger: logging.Logger, message: str, **fields) -> None:
    logger.info(message, extra={"extra_fields": fields})
