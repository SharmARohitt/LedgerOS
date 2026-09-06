from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RoutingDecision:
    model: str
    model_version: str
    routing_policy: str
    temperature: float
    prompt_version: str


@dataclass
class InferenceResult:
    text: str
    inference_mode: str  # LIVE | FALLBACK
    model: str
    model_version: str
    prompt_version: str
    latency_ms: int
    estimated_cost: float
    input_tokens: int | None
    output_tokens: int | None


class InferenceRouter(ABC):
    """Routes a reasoning task by risk x complexity x cost x latency, and
    records everything needed for the observability layer (model, version,
    routing policy, tokens, latency, cost)."""

    @abstractmethod
    def route(self, risk_level: str, complexity: str) -> RoutingDecision: ...

    @abstractmethod
    def explain(self, *, risk_level: str, complexity: str, evidence: dict) -> InferenceResult: ...
