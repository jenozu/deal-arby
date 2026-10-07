from copy import deepcopy
import pytest
from dealfinder.watchlist import (
    build_search_jobs, find_excluded_terms, get_effective_max_source_price,
    get_enabled_products, get_enabled_sources, get_product_by_id,
    has_exact_model_match, listing_passes_watchlist_filters, validate_watchlist_config,
)


@pytest.fixture
def config():
    return {
        "watchlist": [
            {
                "id": "sony_wh1000xm5", "enabled": True, "name": "Sony WH-1000XM5", "brand": "Sony",
                "category": "electronics", "product_type": "headphones", "model_numbers": ["WH-1000XM5"],
                "search_terms": ["Sony WH-1000XM5", "WH1000XM5"], "exclude_terms": ["case only"],
                "preferred_conditions": ["new", "used_excellent"], "max_source_price": 140,
            },
            {
                "id": "disabled", "enabled": False, "name": "Disabled", "brand": "X", "category": "electronics",
                "product_type": "x", "model_numbers": [], "search_terms": ["disabled"], "exclude_terms": [],
                "preferred_conditions": ["new"], "max_source_price": 50,
            },
        ],
        "search_settings": {"global_max_source_price": 150, "max_results_per_search": 50},
        "listing_filters": {"exclude_global_terms": ["broken", "for parts"], "minimum_title_length": 8, "require_title": True},
        "source_priority": [
            {"source": "ebay", "enabled": True, "priority": 1},
            {"source": "kijiji", "enabled": False, "priority": 2},
        ],
    }


def test_valid_config(config):
    validate_watchlist_config(config)


def test_duplicate_product_rejected(config):
    bad = deepcopy(config)
    bad["watchlist"].append(deepcopy(bad["watchlist"][0]))
    with pytest.raises(ValueError):
        validate_watchlist_config(bad)


def test_enabled_products_and_sources(config):
    assert [p.id for p in get_enabled_products(config)] == ["sony_wh1000xm5"]
    assert [s.source for s in get_enabled_sources(config)] == ["ebay"]


def test_effective_max(config):
    product = get_product_by_id(config, "sony_wh1000xm5")
    assert get_effective_max_source_price(product, config) == 140


def test_excluded_accessory(config):
    product = get_product_by_id(config, "sony_wh1000xm5")
    assert "case only" in find_excluded_terms("Sony WH-1000XM5 Case Only", product, config)
    assert listing_passes_watchlist_filters("Sony WH-1000XM5 Case Only", 20, product, config) is False


def test_exact_model(config):
    product = get_product_by_id(config, "sony_wh1000xm5")
    assert has_exact_model_match("Sony WH-1000XM5 Headphones", product) is True


def test_build_jobs(config):
    jobs = build_search_jobs(config)
    assert len(jobs) == 2
    assert all(job.source == "ebay" for job in jobs)
