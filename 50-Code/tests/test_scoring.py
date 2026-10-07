import pytest
from dealfinder.calculator import DealInputs
from dealfinder.evaluator import ListingContext, evaluate_opportunity
from dealfinder.scoring import calculate_opportunity_score, clamp, qualifies_for_alert, validate_scoring_weights


def build(strategy, price=30, market=180, match=98, price_conf=92):
    listing = ListingContext(
        title="Sony WH-1000XM5", category="electronics", condition="used_excellent",
        marketplace="ebay", listing_id="1", model="WH-1000XM5",
        seller_feedback_percent=99.5, seller_feedback_count=100,
        match_confidence=match, price_confidence=price_conf,
    )
    evaluation = evaluate_opportunity(DealInputs(price, market, "used_excellent"), listing, strategy)
    return listing, evaluation, calculate_opportunity_score(evaluation, listing, strategy)


def test_clamp():
    assert clamp(-1) == 0
    assert clamp(150) == 100


def test_weights_validate(strategy):
    validate_scoring_weights(strategy)


def test_invalid_weights_raise(strategy):
    strategy["scoring"]["weights"]["roi"] = 31
    with pytest.raises(ValueError):
        validate_scoring_weights(strategy)


def test_strong_deal_scores(strategy):
    _, _, score = build(strategy)
    assert 0 < score.total_score <= 100


def test_hard_reject_scores_zero(strategy):
    l, e, _ = build(strategy, price=149)
    score = calculate_opportunity_score(e, l, strategy)
    assert score.total_score == 0
    assert score.rating == "reject"


def test_alert_gate(strategy):
    l, e, s = build(strategy, price=20, market=220)
    assert qualifies_for_alert(s, e, l, strategy) == (s.total_score >= 80)
