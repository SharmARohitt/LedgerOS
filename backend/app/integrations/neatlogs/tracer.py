"""Neatlogs-style flight recorder. No Neatlogs credentials are available in
this environment, so traces/spans are written straight to Postgres (Trace,
Span models) with the same fields a real Neatlogs export would carry
(trace_id, span hierarchy, tool calls, model usage, cost, retries). Swapping
in a real Neatlogs backend later means adding an export step here, not
changing how the rest of the app calls this tracer."""

import hashlib
import json
import time
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.models.observability import Span, Trace

_SECRET_KEYS = {"password", "secret", "token", "api_key", "authorization", "webhook_secret"}


def _redact(value):
    if isinstance(value, dict):
        return {k: ("***REDACTED***" if any(s in k.lower() for s in _SECRET_KEYS) else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    return value


def hash_arguments(args: dict) -> str:
    canonical = json.dumps(_redact(args), sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def start_trace(db: Session, case_id: str | None, workflow_id: str = "investigation") -> Trace:
    trace = Trace(case_id=case_id, workflow_id=workflow_id, status="RUNNING")
    db.add(trace)
    db.flush()
    return trace


def finish_trace(db: Session, trace: Trace, status: str, duration_ms: int, total_cost_estimate: float = 0) -> None:
    trace.status = status
    trace.duration_ms = duration_ms
    trace.total_cost_estimate = total_cost_estimate
    db.flush()


@contextmanager
def span(
    db: Session,
    trace: Trace,
    *,
    agent_id: str,
    tool_name: str,
    arguments: dict | None = None,
    parent_span_id: str | None = None,
):
    """Context manager that records one Span row around a worker's tool call,
    redacting secrets from the hashed arguments and capturing status/duration
    even when the wrapped code raises."""
    rec = Span(
        trace_id=trace.id,
        parent_span_id=parent_span_id,
        agent_id=agent_id,
        tool_name=tool_name,
        tool_arguments_hash=hash_arguments(arguments or {}),
        status="RUNNING",
    )
    db.add(rec)
    db.flush()
    start = time.perf_counter()
    try:
        yield rec
        rec.status = "SUCCESS"
    except Exception as exc:  # noqa: BLE001 - deliberately broad: always record span outcome
        rec.status = "FAILED"
        rec.error = str(exc)
        raise
    finally:
        rec.duration_ms = int((time.perf_counter() - start) * 1000)
        db.flush()
