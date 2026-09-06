from app.domain.risk.engine import RiskSignals, score_risk


def test_exact_match_has_no_amount_signal():
    result = score_risk(RiskSignals(amount=50000, invoice_amount=50000))
    assert "AMOUNT_MISMATCH_MINOR" not in result.signals
    assert result.discrepancy_amount == 0


def test_minor_mismatch_scores_low():
    result = score_risk(RiskSignals(amount=48750, invoice_amount=50000))
    assert "AMOUNT_MISMATCH_MINOR" in result.signals
    assert result.risk_level in ("LOW", "MEDIUM")


def test_missing_invoice_is_high_risk():
    result = score_risk(RiskSignals(amount=87000, invoice_amount=None, has_invoice=False, is_new_vendor=True))
    assert "MISSING_INVOICE" in result.signals
    assert "NEW_VENDOR" in result.signals
    assert result.risk_level in ("HIGH", "CRITICAL")


def test_duplicate_payment_raises_score():
    baseline = score_risk(RiskSignals(amount=15000, invoice_amount=15000))
    duplicate = score_risk(RiskSignals(amount=15000, invoice_amount=15000, is_duplicate_payment=True))
    assert duplicate.risk_score > baseline.risk_score
    assert "DUPLICATE_PAYMENT" in duplicate.signals


def test_score_never_exceeds_100():
    result = score_risk(
        RiskSignals(
            amount=100000,
            invoice_amount=None,
            has_invoice=False,
            is_new_customer=True,
            is_new_vendor=True,
            entity_mismatch=True,
            is_duplicate_payment=True,
            evidence_complete=False,
        )
    )
    assert result.risk_score <= 100
    assert result.risk_level == "CRITICAL"
