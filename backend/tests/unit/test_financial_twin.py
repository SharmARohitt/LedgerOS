from datetime import date, timedelta

from app.domain.financial_twin.engine import FinancialInputs, compute_snapshot

TODAY = date(2026, 1, 1)


def _inputs(**overrides) -> FinancialInputs:
    base = dict(
        accounts=[
            {"id": "a1", "name": "Operating", "account_type": "OPERATING", "balance": 2_600_000.0, "is_restricted": False},
            {"id": "a2", "name": "Reserve", "account_type": "RESERVE", "balance": 2_000_000.0, "is_restricted": True},
        ],
        receivables=[
            {"invoice_id": "i1", "invoice_number": "INV-1", "remaining": 48_750.0, "due_date": (TODAY + timedelta(days=15)).isoformat()},
        ],
        obligations=[
            {"id": "o1", "obligation_type": "PAYROLL", "description": "Payroll", "counterparty": "Payroll", "amount": 620_000.0, "due_date": (TODAY + timedelta(days=12)).isoformat(), "status": "SCHEDULED"},
            {"id": "o2", "obligation_type": "VENDOR", "description": "Cloud", "counterparty": "CloudCore", "amount": 380_000.0, "due_date": (TODAY + timedelta(days=10)).isoformat(), "status": "SCHEDULED"},
            {"id": "o3", "obligation_type": "DEBT", "description": "Loan", "counterparty": "Bank", "amount": 300_000.0, "due_date": (TODAY + timedelta(days=45)).isoformat(), "status": "SCHEDULED"},
        ],
        minimum_reserve=3_000_000.0,
        operational_buffer=500_000.0,
        policy_version="V1.0",
        exceptions_open=0,
        at_risk_capital=0.0,
    )
    base.update(overrides)
    return FinancialInputs(**base)


def test_total_cash_sums_all_accounts():
    snapshot = compute_snapshot(_inputs(), as_of=TODAY)
    assert snapshot["cash"]["total_cash"] == 4_600_000.0


def test_deployable_capital_respects_reserve_and_buffer():
    snapshot = compute_snapshot(_inputs(), as_of=TODAY)
    # 4.6M cash - 3.0M reserve - 0.5M buffer = 1.1M
    assert snapshot["capital_map"]["deployable_capital"] == 1_100_000.0


def test_deployable_capital_floors_at_zero_when_cash_below_reserve():
    snapshot = compute_snapshot(_inputs(minimum_reserve=10_000_000.0), as_of=TODAY)
    assert snapshot["capital_map"]["deployable_capital"] == 0.0


def test_committed_outflows_only_counts_scheduled_within_window():
    snapshot = compute_snapshot(_inputs(), as_of=TODAY)
    # payroll (620k, 12d) + cloudcore (380k, 10d) within 30d; debt (300k, 45d) excluded
    assert snapshot["capital_map"]["committed_outflows"] == 1_000_000.0


def test_debt_reduction_opportunity_appears_when_debt_outstanding():
    snapshot = compute_snapshot(_inputs(), as_of=TODAY)
    categories = {o["category"] for o in snapshot["deployment_opportunities"]}
    assert "DEBT_REDUCTION" in categories


def test_no_opportunities_when_no_deployable_capital():
    snapshot = compute_snapshot(_inputs(minimum_reserve=10_000_000.0), as_of=TODAY)
    assert snapshot["deployment_opportunities"] == []


def test_vendor_concentration_warning_fires_above_threshold():
    snapshot = compute_snapshot(_inputs(), as_of=TODAY)
    signals = {w["signal"] for w in snapshot["early_warnings"]}
    assert "VENDOR_CONCENTRATION" in signals  # CloudCore is 100% of vendor spend here


def test_liquidity_pressure_warning_fires_when_projected_cash_below_reserve():
    # Blow out obligations so the 30-day projection dips below the reserve.
    inputs = _inputs()
    inputs.obligations.append(
        {
            "id": "o4",
            "obligation_type": "VENDOR",
            "description": "Emergency spend",
            "counterparty": "Other",
            "amount": 5_000_000.0,
            "due_date": (TODAY + timedelta(days=5)).isoformat(),
            "status": "SCHEDULED",
        }
    )
    snapshot = compute_snapshot(inputs, as_of=TODAY)
    signals = {w["signal"] for w in snapshot["early_warnings"]}
    assert "LIQUIDITY_PRESSURE" in signals


def test_no_deployment_opportunities_never_auto_status():
    snapshot = compute_snapshot(_inputs(), as_of=TODAY)
    for opp in snapshot["deployment_opportunities"]:
        assert opp["status"] in ("REVIEW_REQUIRED", "CFO_APPROVAL")
