"""AO-style worker orchestration. No AO SDK/credentials are available in this
environment, so this module is a local implementation of the same worker/case
contract AO exposes (register a worker, dispatch a case to it, track status),
kept behind this interface so a real AO client can be substituted later
without touching agents/orchestrator.py."""

from dataclasses import dataclass
from enum import Enum
from typing import Callable


class WorkerStatus(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


@dataclass
class WorkerResult:
    status: WorkerStatus
    output: dict
    error: str | None = None


class WorkforceRegistry:
    """Minimal in-process worker registry. Each worker is a callable
    (case_state: dict) -> WorkerResult, matching AO's worker contract."""

    def __init__(self):
        self._workers: dict[str, Callable[[dict], WorkerResult]] = {}

    def register(self, name: str, fn: Callable[[dict], WorkerResult]) -> None:
        self._workers[name] = fn

    def dispatch(self, name: str, case_state: dict) -> WorkerResult:
        if name not in self._workers:
            return WorkerResult(status=WorkerStatus.FAILED, output={}, error=f"unregistered worker: {name}")
        return self._workers[name](case_state)

    @property
    def registered_workers(self) -> list[str]:
        return list(self._workers.keys())
