import pytest


@pytest.fixture
def strategy():
    return {
        "purchase_limits": {"minimum_purchase_price": 10, "maximum_purchase_price": 150},
        "profit_requirements": {
            "minimum_net_profit": 25,
            "minimum_roi_percent": 35,
            "minimum_profit_margin_percent": 15,
            "minimum_discount_to_market_percent": 20,
        },
        "valuation": {"quick_sale_discount_percent": 10, "minimum_price_confidence": 70},
        "costs": {
            "include_purchase_tax": True,
            "purchase_tax_percent": 13,
            "default_selling_fee_percent": 13,
            "default_outbound_shipping": 15,
            "default_other_costs": 2,
        },
        "condition": {
            "allowed": ["new", "new_open_box", "used_like_new", "used_excellent", "used_good"],
            "excluded": ["for_parts", "broken", "damaged", "unknown"],
            "resale_adjustments": {
                "new": 1.0,
                "new_open_box": 0.95,
                "used_like_new": 0.92,
                "used_excellent": 0.88,
                "used_good": 0.80,
            },
        },
        "categories": {"enabled": ["electronics", "tools", "clothing", "shoes"], "disabled": ["food"]},
        "matching": {"minimum_match_confidence": 80, "strong_match_confidence": 95},
        "risk_filters": {"reject_phrases": ["for parts", "not working", "replica", "fake", "read description"]},
        "scoring": {
            "weights": {
                "roi": 30,
                "net_profit": 25,
                "discount_to_market": 15,
                "price_confidence": 10,
                "match_confidence": 10,
                "condition": 5,
                "seller_quality": 5,
            },
            "thresholds": {"exceptional": 90, "strong": 80, "investigate": 70, "weak": 60, "reject_below": 60},
        },
        "alerts": {"enabled": True, "minimum_score": 80, "minimum_profit": 25, "minimum_roi_percent": 35, "minimum_match_confidence": 80},
    }
