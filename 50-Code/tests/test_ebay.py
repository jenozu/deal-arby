import json
from io import BytesIO
from urllib.error import HTTPError

import pytest

from dealfinder.database import DealFinderDatabase
from dealfinder.sources.ebay import (
    EbayClient,
    EbayConfig,
    EbayConfigurationError,
    EbayRateLimitError,
    build_search_params,
    normalize_ebay_condition,
    normalize_item_summary,
    persist_listings,
)
from dealfinder.watchlist import SearchJob


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def job():
    return SearchJob(
        source="ebay",
        source_priority=1,
        product_id="sony_wh1000xm5",
        product_name="Sony WH-1000XM5",
        brand="Sony",
        category="electronics",
        product_type="headphones",
        search_term="Sony WH-1000XM5",
        max_source_price=150,
        preferred_conditions=["new", "used_excellent"],
        exclude_terms=["case only"],
        manual_review_required=False,
    )


def settings(max_results=50):
    return {
        "max_results_per_search": max_results,
        "include_fixed_price": True,
        "include_auctions": False,
    }


def item(item_id="v1|123|0", price="99.99"):
    return {
        "itemId": item_id,
        "title": "Sony WH-1000XM5 Wireless Headphones",
        "itemWebUrl": "https://www.ebay.ca/itm/123",
        "price": {"value": price, "currency": "CAD"},
        "condition": "Very Good",
        "seller": {"username": "seller1", "feedbackPercentage": "99.7", "feedbackScore": 321},
        "shippingOptions": [
            {"shippingCost": {"value": "12.00", "currency": "CAD"}},
            {"shippingCost": {"value": "9.50", "currency": "CAD"}},
        ],
        "itemLocation": {"country": "CA"},
        "image": {"imageUrl": "https://i.ebayimg.com/test.jpg"},
        "buyingOptions": ["FIXED_PRICE"],
    }


def test_config_from_env_and_urls():
    config = EbayConfig.from_env({
        "EBAY_CLIENT_ID": "id",
        "EBAY_CLIENT_SECRET": "secret",
        "EBAY_ENVIRONMENT": "production",
    })
    assert config.base_url == "https://api.ebay.com"
    assert config.token_url.endswith("/identity/v1/oauth2/token")
    assert config.marketplace_id == "EBAY_CA"


def test_missing_credentials_rejected():
    with pytest.raises(EbayConfigurationError):
        EbayConfig.from_env({})


def test_condition_normalization():
    assert normalize_ebay_condition("Open box") == "new_open_box"
    assert normalize_ebay_condition("Very Good") == "used_excellent"
    assert normalize_ebay_condition("For parts or not working") == "for_parts"
    assert normalize_ebay_condition(None) == "unknown"


def test_build_search_params_uses_price_currency_and_fixed_price():
    params = build_search_params(job(), settings(), EbayConfig("id", "secret"))
    assert params["q"] == "Sony WH-1000XM5"
    assert "price:[..150]" in params["filter"]
    assert "priceCurrency:CAD" in params["filter"]
    assert "buyingOptions:{FIXED_PRICE}" in params["filter"]


def test_normalize_item_summary():
    listing = normalize_item_summary(item())
    assert listing.source == "ebay"
    assert listing.price == pytest.approx(99.99)
    assert listing.shipping_price == pytest.approx(9.50)
    assert listing.total_price == pytest.approx(109.49)
    assert listing.condition == "used_excellent"
    assert listing.seller_feedback_percent == pytest.approx(99.7)


def test_token_is_cached_and_search_normalizes_results():
    calls = []

    def transport(request, timeout):
        calls.append((request.full_url, request.get_method(), request.data, dict(request.header_items())))
        if "/identity/v1/oauth2/token" in request.full_url:
            return FakeResponse({"access_token": "token-1", "expires_in": 7200, "token_type": "Application Access Token"})
        return FakeResponse({"itemSummaries": [item()]})

    client = EbayClient(EbayConfig("id", "secret"), transport=transport, sleeper=lambda _: None, clock=lambda: 1000)
    first = client.search_job(job(), settings())
    second = client.search_job(job(), settings())

    assert first[0].listing_id == "v1|123|0"
    assert second[0].listing_id == "v1|123|0"
    token_calls = [c for c in calls if "/identity/v1/oauth2/token" in c[0]]
    assert len(token_calls) == 1
    search_calls = [c for c in calls if "/item_summary/search" in c[0]]
    assert len(search_calls) == 2
    assert any(k.lower() == "x-ebay-c-marketplace-id" and v == "EBAY_CA" for k, v in search_calls[0][3].items())


def test_pagination_stops_at_max_results():
    search_count = 0

    def transport(request, timeout):
        nonlocal search_count
        if "/identity/v1/oauth2/token" in request.full_url:
            return FakeResponse({"access_token": "token-1", "expires_in": 7200})
        search_count += 1
        if search_count == 1:
            return FakeResponse({"itemSummaries": [item("v1|1|0"), item("v1|2|0")], "next": "page-2"})
        return FakeResponse({"itemSummaries": [item("v1|3|0")]})

    client = EbayClient(EbayConfig("id", "secret"), transport=transport, sleeper=lambda _: None, clock=lambda: 1000)
    results = client.search_job(job(), settings(max_results=3))
    assert [r.listing_id for r in results] == ["v1|1|0", "v1|2|0", "v1|3|0"]
    assert search_count == 2


def test_rate_limit_retries_then_raises():
    sleeps = []

    def transport(request, timeout):
        if "/identity/v1/oauth2/token" in request.full_url:
            return FakeResponse({"access_token": "token-1", "expires_in": 7200})
        raise HTTPError(request.full_url, 429, "Too Many Requests", {}, BytesIO(b'{"errors":[]}'))

    client = EbayClient(
        EbayConfig("id", "secret", max_retries=2),
        transport=transport,
        sleeper=sleeps.append,
        clock=lambda: 1000,
    )
    with pytest.raises(EbayRateLimitError):
        client.search_job(job(), settings())
    assert sleeps == [1, 2]


def test_persist_listings_upserts_duplicates(tmp_path):
    db = DealFinderDatabase(str(tmp_path / "db.sqlite"))
    listing = normalize_item_summary(item())
    first = persist_listings(db, [listing], job())
    second = persist_listings(db, [listing], job())
    assert first == second
    assert db.get_statistics()["listings"] == 1
    stored = db.get_listing("ebay", listing.listing_id)
    assert stored["purchase_price"] == pytest.approx(listing.total_price)
