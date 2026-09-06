"""TensorMux-style inference routing. No TensorMux credentials are available
in this environment, so routing is implemented locally with the same
interface a real TensorMux client would fill in. Model tiers below are the
Anthropic models this router would call when ANTHROPIC_API_KEY is set;
without it, every call falls back to a deterministic template and is tagged
inference_mode=FALLBACK end-to-end so the UI never presents a template as a
live model call."""

import time

from app.core.config import get_settings
from app.integrations.tensormux.base import InferenceResult, InferenceRouter, RoutingDecision

PROMPT_VERSION = "explain-v1"

_TIERS = {
    "LOW": ("claude-haiku-4-5-20251001", "fast_low_cost"),
    "MEDIUM": ("claude-sonnet-5", "balanced"),
    "HIGH": ("claude-opus-5", "highest_confidence"),
    "CRITICAL": ("claude-opus-5", "highest_confidence"),
}


class LocalInferenceRouter(InferenceRouter):
    def __init__(self):
        settings = get_settings()
        self._anthropic_key = settings.anthropic_api_key

    def route(self, risk_level: str, complexity: str) -> RoutingDecision:
        model, policy = _TIERS.get(risk_level, _TIERS["MEDIUM"])
        return RoutingDecision(
            model=model,
            model_version="2026-01",
            routing_policy=policy,
            temperature=0.0 if risk_level in ("HIGH", "CRITICAL") else 0.2,
            prompt_version=PROMPT_VERSION,
        )

    def explain(self, *, risk_level: str, complexity: str, evidence: dict) -> InferenceResult:
        routing = self.route(risk_level, complexity)
        start = time.perf_counter()

        if self._anthropic_key:
            text, input_tokens, output_tokens = self._call_anthropic(routing.model, evidence)
            mode = "LIVE"
            cost = self._estimate_cost(routing.model, input_tokens, output_tokens)
        else:
            text = self._template_explanation(evidence)
            input_tokens = output_tokens = None
            mode = "FALLBACK"
            cost = 0.0

        latency_ms = int((time.perf_counter() - start) * 1000)
        return InferenceResult(
            text=text,
            inference_mode=mode,
            model=routing.model if mode == "LIVE" else "template",
            model_version=routing.model_version if mode == "LIVE" else "n/a",
            prompt_version=routing.prompt_version,
            latency_ms=latency_ms,
            estimated_cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _call_anthropic(self, model: str, evidence: dict) -> tuple[str, int, int]:
        import anthropic

        client = anthropic.Anthropic(api_key=self._anthropic_key)
        prompt = (
            "You are the Decision Worker in an autonomous finance control plane. "
            "Explain in 2-3 sentences, in plain language for a CFO, why this case "
            f"should resolve the way the evidence indicates.\n\nEvidence:\n{evidence}"
        )
        response = client.messages.create(
            model=model,
            max_tokens=220,
            temperature=0.0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if hasattr(block, "text"))
        return text, response.usage.input_tokens, response.usage.output_tokens

    def _template_explanation(self, evidence: dict) -> str:
        parts = []
        if evidence.get("invoice_number"):
            parts.append(f"Payment was matched to invoice {evidence['invoice_number']}.")
        if evidence.get("discrepancy_amount") is not None:
            parts.append(f"A discrepancy of ${abs(evidence['discrepancy_amount']):,.2f} was detected.")
        if evidence.get("credit_memo_number"):
            parts.append(
                f"This is fully explained by credit memo {evidence['credit_memo_number']} "
                f"for ${abs(evidence.get('credit_memo_amount', 0)):,.2f} under {evidence.get('policy_version', 'the applicable policy')}."
            )
        if evidence.get("similar_case_stats"):
            s = evidence["similar_case_stats"]
            if s.get("total_cases"):
                parts.append(
                    f"Similar historical cases were approved {s.get('approved', 0)}/{s.get('total_cases', 0)} times."
                )
        if not parts:
            parts.append("Evidence was insufficient to construct a confident automated explanation.")
        return " ".join(parts)

    @staticmethod
    def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        # Illustrative per-token rates; not a billing-accurate figure.
        rates = {
            "claude-haiku-4-5-20251001": (0.0000008, 0.000004),
            "claude-sonnet-5": (0.000003, 0.000015),
            "claude-opus-5": (0.000015, 0.000075),
        }
        in_rate, out_rate = rates.get(model, (0.000003, 0.000015))
        return round(input_tokens * in_rate + output_tokens * out_rate, 6)
