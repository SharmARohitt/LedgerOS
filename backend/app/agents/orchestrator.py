"""Case orchestrator: runs the Evidence -> Payment -> Policy -> Decision ->
Audit pipeline for one exception, via the AO-style WorkforceRegistry, tracing
every step through the Neatlogs-style tracer. Workers communicate only
through the explicit `case_state` dict — no free-form agent-to-agent chat."""

import json
import time

from sqlalchemy.orm import Session

from app.agents import audit_worker, decision_worker, evidence_worker, payment_worker, policy_worker
from app.integrations.ao.orchestration import WorkerStatus, WorkforceRegistry
from app.integrations.neatlogs.tracer import finish_trace, span, start_trace
from app.models.investigations import CaseTask, ExceptionRecord, InvestigationCase

PIPELINE = ["EVIDENCE", "PAYMENT", "POLICY", "DECISION", "AUDIT"]

_SPAN_FIELD_KEYS = {
    "model",
    "model_version",
    "prompt_version",
    "inference_mode",
    "confidence",
    "risk_level",
    "policy_version",
    "human_approval",
    "cost_estimate",
}


def _patch_span(rec, output: dict) -> None:
    if "decision_type" in output:
        rec.decision = output["decision_type"]
    for key in _SPAN_FIELD_KEYS:
        if key in output and output[key] is not None:
            setattr(rec, key, output[key])


def run_investigation(db: Session, exception_id: str) -> InvestigationCase:
    exception = db.get(ExceptionRecord, exception_id)
    exception.status = "INVESTIGATING"

    case = InvestigationCase(exception_id=exception_id, status="RUNNING")
    db.add(case)
    db.flush()

    trace = start_trace(db, case_id=case.id, workflow_id="investigation")
    case.trace_id = trace.id
    db.flush()

    case_state = {
        "case_id": case.id,
        "exception_id": exception_id,
        "event_id": exception.event_id,
        "trace_id": trace.id,
    }

    registry = WorkforceRegistry()
    registry.register("EVIDENCE", lambda cs: evidence_worker.run(db, cs))
    registry.register("PAYMENT", lambda cs: payment_worker.run(db, cs))
    registry.register("POLICY", lambda cs: policy_worker.run(db, cs))
    registry.register("DECISION", lambda cs: decision_worker.run(db, cs))
    registry.register("AUDIT", lambda cs: audit_worker.run(db, cs))

    start_time = time.perf_counter()
    failed = False

    for worker_name in PIPELINE:
        task = CaseTask(case_id=case.id, worker_name=worker_name, status="RUNNING", input_json=json.dumps(case_state, default=str))
        db.add(task)
        db.flush()
        task_start = time.perf_counter()
        try:
            with span(
                db,
                trace,
                agent_id=f"{worker_name.lower()}_worker",
                tool_name=f"{worker_name.lower()}_worker.run",
                arguments={"case_id": case.id, "worker": worker_name},
            ) as rec:
                result = registry.dispatch(worker_name, case_state)
                if result.status != WorkerStatus.SUCCESS:
                    raise RuntimeError(result.error or f"{worker_name} worker did not succeed")
                _patch_span(rec, result.output)
                task.span_id = rec.id

            task.status = "SUCCESS"
            task.output_json = json.dumps(result.output, default=str)
            case_state[worker_name.lower()] = result.output
        except Exception as exc:  # noqa: BLE001 - a failed worker must not crash the whole request
            task.status = "FAILED"
            task.error = str(exc)
            failed = True
            db.flush()
            break
        finally:
            task.duration_ms = int((time.perf_counter() - task_start) * 1000)
            db.flush()

    total_duration_ms = int((time.perf_counter() - start_time) * 1000)

    if failed:
        case.status = "FAILED"
        exception.status = "OPEN"
        finish_trace(db, trace, status="FAILED", duration_ms=total_duration_ms)
    else:
        decision_type = case_state["decision"]["decision_type"]
        case.status = "COMPLETED" if decision_type == "AUTO_RESOLVE" else "AWAITING_APPROVAL"
        exception.status = {
            "AUTO_RESOLVE": "RESOLVED",
            "BLOCK": "BLOCKED",
            "HUMAN_REVIEW": "INVESTIGATING",
        }[decision_type]
        finish_trace(
            db,
            trace,
            status="SUCCESS",
            duration_ms=total_duration_ms,
            total_cost_estimate=case_state["decision"].get("cost_estimate", 0),
        )

    case.case_state_json = json.dumps(case_state, default=str)
    db.flush()
    return case
