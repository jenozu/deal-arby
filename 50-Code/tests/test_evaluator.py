from dealfinder.calculator import DealInputs
from dealfinder.evaluator import ListingContext, evaluate_opportunity, find_risky_keywords


def listing(**overrides):
    data = dict(
        title="Sony WH-1000XM5 Wireless Headphones",
        category="electronics",
        condition="used_excellent",
        marketplace="ebay",
        listing_id="1",
        model="WH-1000XM5",
        seller_feedback_percent=99.5,
        seller_feedback_count=100,
        match_confidence=98,
        price_confidence=92,
    )
    data.update(overrides)
    return ListingContext(**data)


def test_strong_listing_qualifies(strategy):
    result = evaluate_opportunity(DealInputs(30, 180, "used_excellent"), listing(), strategy)
    assert result.status == "qualified"
    assert result.hard_rejected is False


def test_risky_keyword_rejects(strategy):
    l = listing(title="Sony WH-1000XM5 not working")
    result = evaluate_opportunity(DealInputs(30, 180, "used_excellent"), l, strategy)
    assert result.hard_rejected is True
    assert "not working" in find_risky_keywords(l, strategy)


def test_disabled_category_rejects(strategy):
    result = evaluate_opportunity(DealInputs(30, 180, "used_excellent"), listing(category="food"), strategy)
    assert "category_not_allowed" in result.rejection_reasons


def test_low_confidence_investigate(strategy):
    result = evaluate_opportunity(DealInputs(30, 180, "used_excellent"), listing(match_confidence=60), strategy)
    assert result.status == "investigate"
    assert result.requires_manual_review is True


def test_counterfeit_rejects(strategy):
    result = evaluate_opportunity(DealInputs(30, 180, "used_excellent"), listing(possible_counterfeit=True), strategy)
    assert result.hard_rejected is True
