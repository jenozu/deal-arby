import pytest
from dealfinder.calculator import (
    DealInputs, apply_condition_adjustment, calculate_discount_to_market,
    calculate_profit_margin, calculate_roi, calculate_selling_fees, evaluate_deal,
)


def test_percentage_style_calculations():
    assert calculate_selling_fees(100, 13) == pytest.approx(13)
    assert calculate_roi(25, 100) == pytest.approx(25)
    assert calculate_profit_margin(25, 100) == pytest.approx(25)
    assert calculate_discount_to_market(60, 100) == pytest.approx(40)


def test_condition_adjustment():
    assert apply_condition_adjustment(100, "used_good", {"used_good": 0.8}) == pytest.approx(80)


def test_unknown_condition_raises():
    with pytest.raises(ValueError):
        apply_condition_adjustment(100, "broken", {"new": 1.0})


def test_strong_deal_qualifies(strategy):
    result = evaluate_deal(DealInputs(30, 180, "used_excellent"), strategy)
    assert result.financially_qualified is True
    assert result.estimated_profit > 25
    assert result.roi_percent > 35
    assert result.maximum_buy_price > 0


def test_expensive_deal_rejected(strategy):
    result = evaluate_deal(DealInputs(145, 180, "used_excellent"), strategy)
    assert result.financially_qualified is False
    assert result.rejection_reasons


def test_result_serializes(strategy):
    result = evaluate_deal(DealInputs(30, 180, "new"), strategy)
    assert result.to_dict()["purchase_price"] == 30
