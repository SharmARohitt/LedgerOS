from datetime import date, timedelta

from app.domain.financial_twin.engine import FinancialInputs
from app.domain.simulations.engine import run_scenario

TODAY = date(2026, 1, 1)


def _inputs() -> FinancialInputs:
    return FinancialInputs(
        accounts=[{"id": "a1", "name": "Operating", "account_type": "OPERATING", "balance": 2_600_000.0, "is_restricted": False}],
        receivables=[
            {"invoice_id": "i1", "invoice_number": "INV-1", "remaining": 100_000.0, "due_date": (TODAY + timedelta(days=10)).isoformat()},
        ],
        obligations=[
            {"id": "o1", "obligation_type": "VENDOR", "description": "Cloud", "counterparty": "CloudCore", "amount": 200_000.0, "due_date": (TODAY + timedelta(days=10)).isoformat(), "status": "SCHEDULED"},
        ],
        minimum_reserve=1_000_000.0,
        operational_buffer=200_000.0,
        policy_version="V1.0",
        exceptions_open=0,
        at_risk_capital=0.0,
    )


def test_funding_increase_raises_total_cash():
    result = run_scenario(_inputs(), "FUNDING_CHANGE", {"pct": 20}, as_of=TODAY)
    assert result["scenario"]["cash"]["total_cash"] > result["baseline"]["cash"]["total_cash"]
    assert result["deltas"]["total_cash"] > 0


def test_revenue_decline_lowers_expected_inflows():
    result = run_scenario(_inputs(), "REVENUE_CHANGE", {"pct": -20}, as_of=TODAY)
    assert result["scenario"]["capital_map"]["expected_inflows"] < result["baseline"]["capital_map"]["expected_inflows"]


def test_expense_increase_raises_committed_outflows():
    result = run_scenario(_inputs(), "EXPENSE_CHANGE", {"pct": 15}, as_of=TODAY)
    assert result["scenario"]["capital_map"]["committed_outflows"] > result["baseline"]["capital_map"]["committed_outflows"]


def test_delay_payment_moves_obligation_outside_window():
    # Delaying the only obligation (due in 10 days) by 25 days pushes it past
    # the 30-day forecast window, so committed_outflows for that window drops.
    result = run_scenario(_inputs(), "DELAY_PAYMENT", {"days": 25, "obligation_id": "o1"}, as_of=TODAY)
    assert result["scenario"]["capital_map"]["committed_outflows"] < result["baseline"]["capital_map"]["committed_outflows"]


def test_baseline_is_deterministic_and_unaffected_by_scenario_type():
    result_a = run_scenario(_inputs(), "FUNDING_CHANGE", {"pct": 20}, as_of=TODAY)
    result_b = run_scenario(_inputs(), "EXPENSE_CHANGE", {"pct": 15}, as_of=TODAY)
    assert result_a["baseline"] == result_b["baseline"]


def test_scenario_result_is_labeled_simulated():
    result = run_scenario(_inputs(), "FUNDING_CHANGE", {"pct": 20}, as_of=TODAY)
    assert "SIMULATED" in result["label"]
