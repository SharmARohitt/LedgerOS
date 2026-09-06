"""Policy evaluation against a versioned Policy row. Thresholds always come
from the Policy's rules_json — never hardcoded — so a new policy version
never silently rewrites the interpretation of a past decision."""

import json
from dataclasses import dataclass

DEFAULT_APPROVAL_RULES = {
    "auto_resolve_max_amount": 5000,
    "human_review_max_amount": 25000,
    "block_new_vendor_without_invoice": True,
    "block_missing_evidence": True,
    "sla_credit_tolerance": 5.00,  # dollars of slack when matching a credit memo to a discrepancy
}


@dataclass
class PolicyInput:
    discrepancy_amount: float | None
    credit_memo_amount: float | None
    has_invoice: bool
    has_credit_memo_match: bool
    is_new_vendor: bool
    evidence_complete: bool
    risk_level: str


@dataclass
class PolicyVerdict:
    decision_type: str  # AUTO_RESOLVE | HUMAN_REVIEW | BLOCK
    reason: str
    matched_rule: str


def load_rules(rules_json: str) -> dict:
    try:
        parsed = json.loads(rules_json)
        return {**DEFAULT_APPROVAL_RULES, **parsed} if isinstance(parsed, dict) else DEFAULT_APPROVAL_RULES
    except (json.JSONDecodeError, TypeError):
        return DEFAULT_APPROVAL_RULES


def evaluate(policy_input: PolicyInput, rules: dict) -> PolicyVerdict:
    if not policy_input.has_invoice:
        if policy_input.is_new_vendor and rules.get("block_new_vendor_without_invoice", True):
            return PolicyVerdict(
                decision_type="BLOCK",
                reason="No matching invoice found and counterparty is a new, unverified vendor.",
                matched_rule="block_new_vendor_without_invoice",
            )
        return PolicyVerdict(
            decision_type="HUMAN_REVIEW",
            reason="No matching invoice found for this payment.",
            matched_rule="missing_invoice_requires_review",
        )

    if not policy_input.evidence_complete and rules.get("block_missing_evidence", True):
        return PolicyVerdict(
            decision_type="HUMAN_REVIEW",
            reason="Evidence chain is incomplete; insufficient basis for automatic resolution.",
            matched_rule="block_missing_evidence",
        )

    amount = abs(policy_input.discrepancy_amount or 0)
    tolerance = rules.get("sla_credit_tolerance", 5.00)

    explained_by_credit_memo = (
        policy_input.has_credit_memo_match
        and policy_input.credit_memo_amount is not None
        and abs(abs(policy_input.credit_memo_amount) - amount) <= tolerance
    )

    if amount <= 0.01:
        return PolicyVerdict(decision_type="AUTO_RESOLVE", reason="Payment matches invoice exactly.", matched_rule="exact_match")

    if explained_by_credit_memo and policy_input.risk_level in ("LOW", "MEDIUM"):
        auto_max = rules.get("auto_resolve_max_amount", 5000)
        if amount <= auto_max:
            return PolicyVerdict(
                decision_type="AUTO_RESOLVE",
                reason=f"Discrepancy of ${amount:,.2f} is fully explained by a matching credit memo within policy tolerance.",
                matched_rule="auto_resolve_max_amount",
            )
        return PolicyVerdict(
            decision_type="HUMAN_REVIEW",
            reason=f"Discrepancy of ${amount:,.2f} is explained by a credit memo but exceeds the auto-resolve limit of ${auto_max:,.2f}.",
            matched_rule="human_review_max_amount",
        )

    human_max = rules.get("human_review_max_amount", 25000)
    if amount <= human_max and policy_input.risk_level != "CRITICAL":
        return PolicyVerdict(
            decision_type="HUMAN_REVIEW",
            reason=f"Discrepancy of ${amount:,.2f} is not fully explained by available evidence.",
            matched_rule="human_review_max_amount",
        )

    return PolicyVerdict(
        decision_type="BLOCK",
        reason=f"Discrepancy of ${amount:,.2f} exceeds policy limits or carries critical risk signals.",
        matched_rule="block_over_limit_or_critical_risk",
    )
