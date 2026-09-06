"""Financial Twin: a deterministic capital model computed from real backend
state (bank accounts, invoices, obligations, policy). No number here is
hardcoded in the frontend — every value in FinancialSnapshot is derived from
FinancialInputs, which is gathered fresh from the database by
gather_inputs(). The same compute_snapshot() function is used for both the
real "current state" view and every scenario recalculation, so baseline and
scenario numbers can never drift from different formulas."""

import json
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.contracts import Policy
from app.models.finance import CreditMemo, Invoice, Payment
from app.models.investigations import ExceptionRecord
from app.models.treasury import BankAccount, Obligation

DEFAULT_RESERVE_RULES = {"minimum_reserve": 3_000_000.0, "operational_buffer": 500_000.0}
CAPITAL_RESERVE_POLICY_KEY = "capital_reserve"
FORECAST_WINDOW_DAYS = 30


@dataclass
class FinancialInputs:
    accounts: list[dict]  # [{id, name, account_type, balance, is_restricted}]
    receivables: list[dict]  # [{invoice_id, invoice_number, remaining, due_date, customer_name}]
    obligations: list[dict]  # [{id, obligation_type, description, counterparty, amount, due_date, status}]
    minimum_reserve: float
    operational_buffer: float
    policy_version: str | None
    exceptions_open: int
    at_risk_capital: float


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def gather_inputs(db: Session) -> FinancialInputs:
    accounts = [
        {
            "id": a.id,
            "name": a.name,
            "account_type": a.account_type,
            "balance": float(a.current_balance),
            "is_restricted": a.is_restricted,
        }
        for a in db.query(BankAccount).all()
    ]

    receivables = []
    for inv in db.query(Invoice).filter(Invoice.status.in_(["OPEN", "PARTIAL"])).all():
        paid = db.query(func.coalesce(func.sum(Payment.amount), 0)).filter(
            Payment.invoice_id == inv.id, Payment.status == "SUCCEEDED"
        ).scalar()
        credited = db.query(func.coalesce(func.sum(CreditMemo.amount), 0)).filter(
            CreditMemo.invoice_id == inv.id
        ).scalar()
        remaining = float(inv.total_amount) - float(paid or 0) - abs(float(credited or 0))
        if remaining <= 0.01:
            continue
        receivables.append(
            {
                "invoice_id": inv.id,
                "invoice_number": inv.invoice_number,
                "remaining": round(remaining, 2),
                "due_date": inv.due_date,
            }
        )

    obligations = [
        {
            "id": o.id,
            "obligation_type": o.obligation_type,
            "description": o.description,
            "counterparty": o.counterparty,
            "amount": float(o.amount),
            "due_date": o.due_date,
            "status": o.status,
        }
        for o in db.query(Obligation).all()
    ]

    policy = (
        db.query(Policy)
        .filter(Policy.policy_key == CAPITAL_RESERVE_POLICY_KEY, Policy.status == "ACTIVE")
        .one_or_none()
    )
    rules = DEFAULT_RESERVE_RULES
    policy_version = None
    if policy is not None:
        try:
            rules = {**DEFAULT_RESERVE_RULES, **json.loads(policy.rules_json)}
        except (json.JSONDecodeError, TypeError):
            rules = DEFAULT_RESERVE_RULES
        policy_version = policy.version

    exceptions_open = db.query(ExceptionRecord).filter(ExceptionRecord.status.in_(["OPEN", "INVESTIGATING"])).count()
    at_risk_capital = (
        db.query(func.coalesce(func.sum(ExceptionRecord.discrepancy_amount), 0))
        .filter(ExceptionRecord.status.in_(["OPEN", "INVESTIGATING"]))
        .scalar()
    )

    return FinancialInputs(
        accounts=accounts,
        receivables=receivables,
        obligations=obligations,
        minimum_reserve=float(rules.get("minimum_reserve", DEFAULT_RESERVE_RULES["minimum_reserve"])),
        operational_buffer=float(rules.get("operational_buffer", DEFAULT_RESERVE_RULES["operational_buffer"])),
        policy_version=policy_version,
        exceptions_open=exceptions_open,
        at_risk_capital=abs(float(at_risk_capital or 0)),
    )


def _within_window(due_date: str | None, today: date, window_days: int) -> bool:
    d = _parse_date(due_date)
    if d is None:
        return False
    return today <= d <= today + timedelta(days=window_days)


def _is_overdue(due_date: str | None, today: date) -> bool:
    d = _parse_date(due_date)
    return d is not None and d < today


def compute_snapshot(inputs: FinancialInputs, as_of: date | None = None) -> dict:
    today = as_of or datetime.now(timezone.utc).date()

    operating_cash = sum(a["balance"] for a in inputs.accounts if a["account_type"] == "OPERATING")
    reserve_cash = sum(
        a["balance"] for a in inputs.accounts if a["account_type"] in ("RESERVE", "PAYROLL") or a["is_restricted"]
    )
    total_cash = operating_cash + reserve_cash

    expected_inflows_30d = sum(r["remaining"] for r in inputs.receivables if _within_window(r["due_date"], today, FORECAST_WINDOW_DAYS))
    committed_outflows_30d = sum(
        o["amount"]
        for o in inputs.obligations
        if o["status"] == "SCHEDULED" and _within_window(o["due_date"], today, FORECAST_WINDOW_DAYS)
    )

    accounts_receivable = sum(r["remaining"] for r in inputs.receivables)
    accounts_payable = sum(o["amount"] for o in inputs.obligations if o["status"] == "SCHEDULED")
    overdue_receivable = sum(r["remaining"] for r in inputs.receivables if _is_overdue(r["due_date"], today))
    overdue_obligations = sum(
        o["amount"] for o in inputs.obligations if o["status"] in ("SCHEDULED", "OVERDUE") and _is_overdue(o["due_date"], today)
    )

    total_capital = total_cash + expected_inflows_30d - committed_outflows_30d
    deployable_capital = max(0.0, total_cash - inputs.minimum_reserve - inputs.operational_buffer)
    net_30d_position = expected_inflows_30d - committed_outflows_30d
    monthly_burn = committed_outflows_30d
    runway_months = round(total_cash / monthly_burn, 1) if monthly_burn > 0 else None

    obligations_by_type: dict[str, float] = {}
    for o in inputs.obligations:
        if o["status"] == "SCHEDULED":
            obligations_by_type[o["obligation_type"]] = obligations_by_type.get(o["obligation_type"], 0.0) + o["amount"]

    vendor_spend: dict[str, float] = {}
    for o in inputs.obligations:
        if o["obligation_type"] == "VENDOR":
            vendor_spend[o["counterparty"]] = vendor_spend.get(o["counterparty"], 0.0) + o["amount"]
    total_vendor_spend = sum(vendor_spend.values())
    top_vendor_concentration = (max(vendor_spend.values()) / total_vendor_spend) if total_vendor_spend > 0 else 0.0
    top_vendor = max(vendor_spend, key=vendor_spend.get) if vendor_spend else None

    liquidity_score = round(min(100.0, 100.0 * total_cash / max(inputs.minimum_reserve + inputs.operational_buffer, 1)))
    collection_health = round(100.0 - min(100.0, 100.0 * overdue_receivable / accounts_receivable)) if accounts_receivable > 0 else 100
    spend_health = round(100.0 - min(100.0, 100.0 * overdue_obligations / accounts_payable)) if accounts_payable > 0 else 100
    vendor_concentration_score = round(top_vendor_concentration * 100, 1)
    data_points = len(inputs.obligations) + len(inputs.receivables) + len(inputs.accounts)
    forecast_confidence = min(90, 40 + 2 * data_points)  # illustrative — more source records, higher stated confidence

    opportunities = _rank_capital_opportunities(deployable_capital, inputs.obligations)

    early_warnings = _build_early_warnings(
        deployable_capital=deployable_capital,
        minimum_reserve=inputs.minimum_reserve,
        total_cash=total_cash,
        net_30d_position=net_30d_position,
        top_vendor=top_vendor,
        top_vendor_concentration=top_vendor_concentration,
        top_vendor_spend=vendor_spend.get(top_vendor, 0.0) if top_vendor else 0.0,
    )

    return {
        "as_of": today.isoformat(),
        "policy_version": inputs.policy_version,
        "cash": {
            "operating_cash": round(operating_cash, 2),
            "reserve_cash": round(reserve_cash, 2),
            "total_cash": round(total_cash, 2),
        },
        "capital_map": {
            "total_capital": round(total_capital, 2),
            "operating_cash": round(operating_cash, 2),
            "reserve": round(reserve_cash, 2),
            "expected_inflows": round(expected_inflows_30d, 2),
            "committed_outflows": round(committed_outflows_30d, 2),
            "deployable_capital": round(deployable_capital, 2),
        },
        "liquidity": {
            "available_cash": round(total_cash, 2),
            "expected_inflows_30d": round(expected_inflows_30d, 2),
            "expected_outflows_30d": round(committed_outflows_30d, 2),
            "net_30d_position": round(net_30d_position, 2),
            "runway_months": runway_months,
            "minimum_reserve": round(inputs.minimum_reserve, 2),
            "operational_buffer": round(inputs.operational_buffer, 2),
        },
        "obligations": {
            "total_payable": round(accounts_payable, 2),
            "by_type": {k: round(v, 2) for k, v in obligations_by_type.items()},
        },
        "revenue": {
            "accounts_receivable": round(accounts_receivable, 2),
            "overdue_receivable": round(overdue_receivable, 2),
        },
        "financial_health": {
            "liquidity_score": liquidity_score,
            "collection_health": collection_health,
            "spend_health": spend_health,
            "vendor_concentration_score": vendor_concentration_score,
            "top_vendor": top_vendor,
            "forecast_confidence": forecast_confidence,
        },
        "exceptions": {
            "open_count": inputs.exceptions_open,
            "at_risk_capital": round(inputs.at_risk_capital, 2),
        },
        "deployment_opportunities": opportunities,
        "early_warnings": early_warnings,
    }


def _rank_capital_opportunities(deployable_capital: float, obligations: list[dict]) -> list[dict]:
    """Rule-based, deterministic. Every opportunity is a RECOMMENDATION only —
    per the autonomy policy, capital deployment always requires human
    approval (see AUTONOMY_MATRIX); nothing here is auto-executed."""
    if deployable_capital <= 0:
        return []

    opportunities = []
    remaining = deployable_capital

    treasury_amt = round(deployable_capital * 0.4, 2)
    opportunities.append(
        {
            "rank": 1,
            "category": "TREASURY_ALLOCATION",
            "label": "Treasury Allocation",
            "amount": treasury_amt,
            "liquidity_impact": "LOW",
            "risk": "LOW",
            "status": "REVIEW_REQUIRED",
            "reason": "Low-risk allocation of idle deployable cash into short-term treasury instruments.",
            "projection_label": "SIMULATED",
        }
    )
    remaining -= treasury_amt

    debt_obligations = [o for o in obligations if o["obligation_type"] == "DEBT" and o["status"] == "SCHEDULED"]
    outstanding_debt = sum(o["amount"] for o in debt_obligations)
    if outstanding_debt > 0 and remaining > 0:
        debt_amt = round(min(remaining * 0.5, outstanding_debt), 2)
        opportunities.append(
            {
                "rank": 2,
                "category": "DEBT_REDUCTION",
                "label": "Debt Reduction",
                "amount": debt_amt,
                "liquidity_impact": "MEDIUM",
                "risk": "LOW",
                "status": "REVIEW_REQUIRED",
                "reason": f"Reduces outstanding debt obligations of ${outstanding_debt:,.0f}.",
                "projection_label": "SIMULATED",
            }
        )
        remaining -= debt_amt

    if remaining > 0:
        opportunities.append(
            {
                "rank": len(opportunities) + 1,
                "category": "GROWTH_INVESTMENT",
                "label": "Growth Investment",
                "amount": round(remaining, 2),
                "liquidity_impact": "MEDIUM",
                "risk": "MEDIUM",
                "status": "CFO_APPROVAL",
                "reason": "Remaining deployable capital available for growth initiatives (hiring, infrastructure, acquisition).",
                "projection_label": "SIMULATED",
            }
        )

    return opportunities


def _build_early_warnings(
    *,
    deployable_capital: float,
    minimum_reserve: float,
    total_cash: float,
    net_30d_position: float,
    top_vendor: str | None,
    top_vendor_concentration: float,
    top_vendor_spend: float,
) -> list[dict]:
    warnings = []

    projected_min_cash = total_cash + net_30d_position
    if projected_min_cash < minimum_reserve:
        warnings.append(
            {
                "signal": "LIQUIDITY_PRESSURE",
                "severity": "HIGH",
                "evidence": f"Projected 30-day cash position of ${projected_min_cash:,.0f} is below the ${minimum_reserve:,.0f} minimum reserve.",
                "forecast_impact": round(projected_min_cash - minimum_reserve, 2),
                "recommended_action": "Review upcoming obligations in Cash & Treasury; consider delaying non-critical payments.",
            }
        )

    if top_vendor and top_vendor_concentration >= 0.25:
        warnings.append(
            {
                "signal": "VENDOR_CONCENTRATION",
                "severity": "MEDIUM" if top_vendor_concentration < 0.4 else "HIGH",
                "evidence": f"{top_vendor_concentration * 100:.0f}% of scheduled vendor spend depends on {top_vendor}.",
                "forecast_impact": round(top_vendor_spend, 2),
                "recommended_action": f"Evaluate concentration risk with {top_vendor}; consider diversifying vendor base.",
            }
        )

    if deployable_capital <= 0 and total_cash > 0:
        warnings.append(
            {
                "signal": "NO_DEPLOYABLE_CAPITAL",
                "severity": "LOW",
                "evidence": "Current cash does not exceed the configured minimum reserve and operational buffer.",
                "forecast_impact": 0,
                "recommended_action": "No capital deployment opportunities available until reserve targets are exceeded.",
            }
        )

    return warnings
