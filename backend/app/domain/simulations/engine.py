"""What-if scenario engine. Mutates a copy of the same FinancialInputs the
real Financial Twin uses, then recomputes through the identical
compute_snapshot() formula — so baseline and scenario numbers are guaranteed
to be computed the same way, only the inputs differ. Every result is
labeled SIMULATED/PROJECTED, never confused with actual financial state."""

import copy
from datetime import date, datetime, timedelta

from app.domain.financial_twin.engine import FinancialInputs, compute_snapshot

SCENARIO_TYPES = ("REVENUE_CHANGE", "COLLECTIONS_CHANGE", "FUNDING_CHANGE", "EXPENSE_CHANGE", "DELAY_PAYMENT")


def apply_scenario(baseline_inputs: FinancialInputs, scenario_type: str, params: dict) -> FinancialInputs:
    inputs = copy.deepcopy(baseline_inputs)

    if scenario_type == "REVENUE_CHANGE":
        pct = float(params.get("pct", 0))
        for r in inputs.receivables:
            r["remaining"] = round(r["remaining"] * (1 + pct / 100), 2)

    elif scenario_type == "COLLECTIONS_CHANGE":
        # A collections deterioration/improvement changes how much of AR is
        # actually expected to convert to cash in the forecast window.
        pct = float(params.get("pct", 0))
        for r in inputs.receivables:
            r["remaining"] = round(r["remaining"] * (1 + pct / 100), 2)

    elif scenario_type == "FUNDING_CHANGE":
        pct = float(params.get("pct", 0))
        total_cash = sum(a["balance"] for a in inputs.accounts)
        additional_capital = round(total_cash * pct / 100, 2)
        if inputs.accounts:
            inputs.accounts[0]["balance"] += additional_capital
        else:
            inputs.accounts.append(
                {"id": "scenario_funding", "name": "New Funding", "account_type": "OPERATING", "balance": additional_capital, "is_restricted": False}
            )

    elif scenario_type == "EXPENSE_CHANGE":
        pct = float(params.get("pct", 0))
        for o in inputs.obligations:
            if o["status"] == "SCHEDULED":
                o["amount"] = round(o["amount"] * (1 + pct / 100), 2)

    elif scenario_type == "DELAY_PAYMENT":
        days = int(params.get("days", 0))
        obligation_id = params.get("obligation_id")
        for o in inputs.obligations:
            if obligation_id and o["id"] != obligation_id:
                continue
            try:
                due = datetime.fromisoformat(o["due_date"])
                o["due_date"] = (due + timedelta(days=days)).date().isoformat()
            except (ValueError, TypeError):
                continue

    return inputs


def run_scenario(baseline_inputs: FinancialInputs, scenario_type: str, params: dict, as_of: date | None = None) -> dict:
    baseline_snapshot = compute_snapshot(baseline_inputs, as_of=as_of)
    scenario_inputs = apply_scenario(baseline_inputs, scenario_type, params)
    scenario_snapshot = compute_snapshot(scenario_inputs, as_of=as_of)

    deltas = _compute_deltas(baseline_snapshot, scenario_snapshot)

    return {
        "scenario_type": scenario_type,
        "params": params,
        "baseline": baseline_snapshot,
        "scenario": scenario_snapshot,
        "deltas": deltas,
        "label": "SIMULATED SCENARIO — NOT ACTUAL FINANCIAL FORECAST",
    }


def _compute_deltas(baseline: dict, scenario: dict) -> dict:
    def delta(path_a, path_b):
        return round(path_b - path_a, 2) if path_a is not None and path_b is not None else None

    return {
        "total_cash": delta(baseline["cash"]["total_cash"], scenario["cash"]["total_cash"]),
        "deployable_capital": delta(
            baseline["capital_map"]["deployable_capital"], scenario["capital_map"]["deployable_capital"]
        ),
        "runway_months": delta(baseline["liquidity"]["runway_months"], scenario["liquidity"]["runway_months"]),
        "net_30d_position": delta(baseline["liquidity"]["net_30d_position"], scenario["liquidity"]["net_30d_position"]),
        "liquidity_score": delta(
            baseline["financial_health"]["liquidity_score"], scenario["financial_health"]["liquidity_score"]
        ),
    }
