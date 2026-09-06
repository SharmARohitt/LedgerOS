"""TensorMux inference routing. TensorMux exposes an OpenAI-compatible chat
completions API (confirmed live at api.tensormux.com, backed by vLLM serving
"glm-4-7-flash") — this is the primary explanation path whenever
TENSORMUX_API_KEY is set. Anthropic is kept as a secondary path for
environments that have ANTHROPIC_API_KEY but not TensorMux. With neither, the
router falls back to a deterministic template and is tagged
inference_mode=FALLBACK end-to-end so the UI never presents a template as a
live model call."""

import time

import httpx

from app.core.config import get_settings
from app.integrations.tensormux.base import InferenceResult, InferenceRouter, RoutingDecision

PROMPT_VERSION = "explain-v1"

# Risk tier -> (temperature, max_tokens, routing_policy). TensorMux currently
# exposes a single model on this account (glm-4-7-flash); risk still drives
# temperature/effort so the routing decision is real even though the model
# name doesn't change. Swap in per-tier models here if the account is granted
# access to more than one.
_TENSORMUX_TIERS = {
    "LOW": (0.2, 200, "fast_low_cost"),
    "MEDIUM": (0.1, 300, "balanced"),
    "HIGH": (0.0, 400, "highest_confidence"),
    "CRITICAL": (0.0, 400, "highest_confidence"),
}

_ANTHROPIC_TIERS = {
    "LOW": ("claude-haiku-4-5-20251001", "fast_low_cost"),
    "MEDIUM": ("claude-sonnet-5", "balanced"),
    "HIGH": ("claude-opus-5", "highest_confidence"),
    "CRITICAL": ("claude-opus-5", "highest_confidence"),
}

_EXPLAIN_PROMPT = (
    "You are the Decision Worker in an autonomous finance control plane. "
    "Explain in 2-3 plain-language sentences, for a CFO, why this case should "
    "resolve the way the evidence indicates. Do not show your reasoning process, "
    "state only the conclusion.\n\nEvidence:\n{evidence}"
)


class LocalInferenceRouter(InferenceRouter):
    def __init__(self):
        self._settings = get_settings()

    def route(self, risk_level: str, complexity: str) -> RoutingDecision:
        settings = self._settings
        if settings.tensormux_is_live:
            _, _, policy = _TENSORMUX_TIERS.get(risk_level, _TENSORMUX_TIERS["MEDIUM"])
            temperature, _, _ = _TENSORMUX_TIERS.get(risk_level, _TENSORMUX_TIERS["MEDIUM"])
            return RoutingDecision(
                model=settings.tensormux_model,
                model_version="tensormux-live",
                routing_policy=policy,
                temperature=temperature,
                prompt_version=PROMPT_VERSION,
            )
        model, policy = _ANTHROPIC_TIERS.get(risk_level, _ANTHROPIC_TIERS["MEDIUM"])
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

        if self._settings.tensormux_is_live:
            try:
                text, input_tokens, output_tokens = self._call_tensormux(risk_level, routing, evidence)
                mode = "LIVE"
                cost = 0.0  # TensorMux billing is account-side; no public per-token rate to estimate against.
                model_name = routing.model
                model_version = routing.model_version
            except (httpx.HTTPError, KeyError, ValueError):
                text = self._template_explanation(evidence)
                input_tokens = output_tokens = None
                mode, cost, model_name, model_version = "FALLBACK", 0.0, "template", "n/a"
        elif self._settings.anthropic_is_live:
            text, input_tokens, output_tokens = self._call_anthropic(routing.model, evidence)
            mode = "LIVE"
            cost = self._estimate_anthropic_cost(routing.model, input_tokens, output_tokens)
            model_name, model_version = routing.model, routing.model_version
        else:
            text = self._template_explanation(evidence)
            input_tokens = output_tokens = None
            mode, cost, model_name, model_version = "FALLBACK", 0.0, "template", "n/a"

        latency_ms = int((time.perf_counter() - start) * 1000)
        return InferenceResult(
            text=text,
            inference_mode=mode,
            model=model_name,
            model_version=model_version,
            prompt_version=routing.prompt_version,
            latency_ms=latency_ms,
            estimated_cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

    def _call_tensormux(self, risk_level: str, routing: RoutingDecision, evidence: dict) -> tuple[str, int, int]:
        settings = self._settings
        _, max_tokens, _ = _TENSORMUX_TIERS.get(risk_level, _TENSORMUX_TIERS["MEDIUM"])
        prompt = _EXPLAIN_PROMPT.format(evidence=evidence)

        response = httpx.post(
            f"{settings.tensormux_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.tensormux_api_key}"},
            json={
                "model": routing.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": routing.temperature,
                # glm-4-7-flash is a reasoning model by default; disable extended
                # thinking so `content` carries the direct answer, not a trace.
                "chat_template_kwargs": {"enable_thinking": False},
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
        message = payload["choices"][0]["message"]
        text = message.get("content") or message.get("reasoning") or ""
        if not text.strip():
            raise ValueError("empty completion from TensorMux")
        usage = payload.get("usage", {})
        return text.strip(), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)

    def _call_anthropic(self, model: str, evidence: dict) -> tuple[str, int, int]:
        import anthropic

        client = anthropic.Anthropic(api_key=self._settings.anthropic_api_key)
        response = client.messages.create(
            model=model,
            max_tokens=220,
            temperature=0.0,
            messages=[{"role": "user", "content": _EXPLAIN_PROMPT.format(evidence=evidence)}],
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
    def _estimate_anthropic_cost(model: str, input_tokens: int, output_tokens: int) -> float:
        # Illustrative per-token rates; not a billing-accurate figure.
        rates = {
            "claude-haiku-4-5-20251001": (0.0000008, 0.000004),
            "claude-sonnet-5": (0.000003, 0.000015),
            "claude-opus-5": (0.000015, 0.000075),
        }
        in_rate, out_rate = rates.get(model, (0.000003, 0.000015))
        return round(input_tokens * in_rate + output_tokens * out_rate, 6)
