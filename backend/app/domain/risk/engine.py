"""Deterministic anomaly/risk scoring. This never calls an LLM — detection is
rule-based; AI is only used downstream to *explain* what the rules found."""

from dataclasses import dataclass, field


@dataclass
class RiskSignals:
    amount: float
    invoice_amount: float | None
    is_new_customer: bool = False
    is_new_vendor: bool = False
    has_invoice: bool = True
    entity_mismatch: bool = False
    is_duplicate_payment: bool = False
    evidence_complete: bool = True
    signals_fired: list[str] = field(default_factory=list)


@dataclass
class RiskResult:
    risk_score: int  # 0-100
    risk_level: str  # LOW | MEDIUM | HIGH | CRITICAL
    signals: list[str]
    discrepancy_amount: float | None


def _level_for_score(score: int) -> str:
    if score >= 80:
        return "CRITICAL"
    if score >= 50:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    return "LOW"


def score_risk(signals: RiskSignals) -> RiskResult:
    score = 0
    fired: list[str] = []

    discrepancy = None
    if signals.has_invoice and signals.invoice_amount is not None:
        discrepancy = round(signals.amount - signals.invoice_amount, 2)
        pct = abs(discrepancy) / signals.invoice_amount if signals.invoice_amount else 0
        if abs(discrepancy) > 0.01:
            if pct <= 0.05:
                score += 10
                fired.append("AMOUNT_MISMATCH_MINOR")
            elif pct <= 0.20:
                score += 30
                fired.append("AMOUNT_MISMATCH_MODERATE")
            else:
                score += 55
                fired.append("AMOUNT_MISMATCH_MAJOR")
    else:
        score += 60
        fired.append("MISSING_INVOICE")

    if signals.is_new_customer:
        score += 15
        fired.append("NEW_CUSTOMER")
    if signals.is_new_vendor:
        score += 25
        fired.append("NEW_VENDOR")
    if signals.entity_mismatch:
        score += 35
        fired.append("ENTITY_MISMATCH")
    if signals.is_duplicate_payment:
        score += 50
        fired.append("DUPLICATE_PAYMENT")
    if not signals.evidence_complete:
        score += 20
        fired.append("MISSING_EVIDENCE")
    if signals.amount >= 25000:
        score += 10
        fired.append("HIGH_VALUE")

    score = min(score, 100)
    return RiskResult(risk_score=score, risk_level=_level_for_score(score), signals=fired, discrepancy_amount=discrepancy)
