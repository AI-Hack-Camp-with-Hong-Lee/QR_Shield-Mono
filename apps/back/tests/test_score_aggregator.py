from app.models.risk import RiskLevel
from app.services.score_aggregator import (
    combine_final_score,
    risk_level_from_score,
)


def test_combine_final_score_adds_rule_and_agent_parts():
    assert combine_final_score(25, 80.0, True, 45) == 100


def test_combine_final_score_without_ml_uses_redirect_only():
    assert combine_final_score(10, None, False, 20) == 30


def test_risk_level_thresholds():
    assert risk_level_from_score(0) is RiskLevel.SAFE
    assert risk_level_from_score(39) is RiskLevel.SAFE
    assert risk_level_from_score(40) is RiskLevel.CAUTION
    assert risk_level_from_score(69) is RiskLevel.CAUTION
    assert risk_level_from_score(70) is RiskLevel.DANGER
