from app.agents.decision_worker import _compute_confidence


def test_auto_resolve_confidence_rises_with_high_historical_approval_rate():
    low_history = _compute_confidence("AUTO_RESOLVE", risk_score=20, approval_rate=0.5)
    high_history = _compute_confidence("AUTO_RESOLVE", risk_score=20, approval_rate=36 / 37)
    assert high_history > low_history


def test_confidence_is_bounded_between_1_and_99():
    assert 1.0 <= _compute_confidence("BLOCK", risk_score=100, approval_rate=0.0) <= 99.0
    assert 1.0 <= _compute_confidence("AUTO_RESOLVE", risk_score=0, approval_rate=1.0) <= 99.0


def test_higher_risk_score_lowers_confidence():
    low_risk = _compute_confidence("AUTO_RESOLVE", risk_score=10, approval_rate=None)
    high_risk = _compute_confidence("AUTO_RESOLVE", risk_score=80, approval_rate=None)
    assert low_risk > high_risk
