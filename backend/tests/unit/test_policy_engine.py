import json

from app.domain.policy.engine import DEFAULT_APPROVAL_RULES, PolicyInput, evaluate, load_rules


def test_case01_shape_auto_resolves():
    policy_input = PolicyInput(
        discrepancy_amount=-1250.00,
        credit_memo_amount=-1250.00,
        has_invoice=True,
        has_credit_memo_match=True,
        is_new_vendor=False,
        evidence_complete=True,
        risk_level="MEDIUM",
    )
    verdict = evaluate(policy_input, DEFAULT_APPROVAL_RULES)
    assert verdict.decision_type == "AUTO_RESOLVE"


def test_missing_invoice_requires_human_review():
    policy_input = PolicyInput(
        discrepancy_amount=None,
        credit_memo_amount=None,
        has_invoice=False,
        has_credit_memo_match=False,
        is_new_vendor=False,
        evidence_complete=False,
        risk_level="HIGH",
    )
    verdict = evaluate(policy_input, DEFAULT_APPROVAL_RULES)
    assert verdict.decision_type == "HUMAN_REVIEW"


def test_new_vendor_without_invoice_is_blocked():
    policy_input = PolicyInput(
        discrepancy_amount=None,
        credit_memo_amount=None,
        has_invoice=False,
        has_credit_memo_match=False,
        is_new_vendor=True,
        evidence_complete=False,
        risk_level="HIGH",
    )
    verdict = evaluate(policy_input, DEFAULT_APPROVAL_RULES)
    assert verdict.decision_type == "BLOCK"


def test_discrepancy_over_auto_resolve_limit_needs_review_even_with_credit_memo():
    policy_input = PolicyInput(
        discrepancy_amount=-8000,
        credit_memo_amount=-8000,
        has_invoice=True,
        has_credit_memo_match=True,
        is_new_vendor=False,
        evidence_complete=True,
        risk_level="MEDIUM",
    )
    verdict = evaluate(policy_input, DEFAULT_APPROVAL_RULES)
    assert verdict.decision_type == "HUMAN_REVIEW"


def test_discrepancy_over_human_review_limit_is_blocked():
    policy_input = PolicyInput(
        discrepancy_amount=-30000,
        credit_memo_amount=None,
        has_invoice=True,
        has_credit_memo_match=False,
        is_new_vendor=False,
        evidence_complete=True,
        risk_level="HIGH",
    )
    verdict = evaluate(policy_input, DEFAULT_APPROVAL_RULES)
    assert verdict.decision_type == "BLOCK"


def test_load_rules_merges_over_defaults():
    rules = load_rules(json.dumps({"auto_resolve_max_amount": 1000}))
    assert rules["auto_resolve_max_amount"] == 1000
    assert rules["human_review_max_amount"] == DEFAULT_APPROVAL_RULES["human_review_max_amount"]


def test_load_rules_falls_back_on_invalid_json():
    assert load_rules("not json") == DEFAULT_APPROVAL_RULES
