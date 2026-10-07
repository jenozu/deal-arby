"""eBay Browse API connector for Deal Arby.

Uses the OAuth client-credentials flow to obtain an Application access token,
then queries the Browse API item_summary/search endpoint.
"""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from ..database import DealFinderDatabase
from ..evaluator import ListingContext
from ..listings import SourceListing
from ..watchlist import SearchJob


EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope"
PRODUCTION_BASE = "https://api.ebay.com"
SANDBOX_BASE = "https://api.sandbox.ebay.com"


class EbayError(RuntimeError):
    pass


class EbayConfigurationError(EbayError):
    pass


class EbayAuthError(EbayError):
    pass


class EbayApiError(EbayError):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class EbayRateLimitError(EbayApiError):
    pass


@dataclass(frozen=True)
class EbayConfig:
    client_id: str
    client_secret: str
    environment: str = "sandbox"
    marketplace_id: str = "EBAY_CA"
    currency: str = "CAD"
    country_code: str = "CA"
    postal_code: Optional[str] = None
    accept_language: Optional[str] = None
    timeout_seconds: float = 20.0
    max_retries: int = 3

    def __post_init__(self) -> None:
        env = self.environment.lower()
        if env not in {"sandbox", "production"}:
            raise EbayConfigurationError("EBAY_ENVIRONMENT must be 'sandbox' or 'production'.")
        if not self.client_id or not self.client_secret:
            raise EbayConfigurationError("EBAY_CLIENT_ID and EBAY_CLIENT_SECRET are required.")
        if self.max_retries < 0:
            raise EbayConfigurationError("max_retries cannot be negative.")

    @property
    def base_url(self) -> str:
        return SANDBOX_BASE if self.environment.lower() == "sandbox" else PRODUCTION_BASE

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/identity/v1/oauth2/token"

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "EbayConfig":
        values = os.environ if env is None else env
        return cls(
            client_id=values.get("EBAY_CLIENT_ID", ""),
            client_secret=values.get("EBAY_CLIENT_SECRET", ""),
            environment=values.get("EBAY_ENVIRONMENT", "sandbox"),
            marketplace_id=values.get("EBAY_MARKETPLACE_ID", "EBAY_CA"),
            currency=values.get("EBAY_CURRENCY", "CAD"),
            country_code=values.get("EBAY_COUNTRY_CODE", "CA"),
            postal_code=values.get("EBAY_POSTAL_CODE") or None,
            accept_language=values.get("EBAY_ACCEPT_LANGUAGE") or None,
            timeout_seconds=float(values.get("EBAY_TIMEOUT_SECONDS", "20")),
            max_retries=int(values.get("EBAY_MAX_RETRIES", "3")),
        )


@dataclass
class EbayAccessToken:
    access_token: str
    expires_at: float
    token_type: str = "Application Access Token"

    def is_valid(self, now: Optional[float] = None, skew_seconds: float = 60.0) -> bool:
        current = time.time() if now is None else now
        return bool(self.access_token) and current < (self.expires_at - skew_seconds)


def normalize_ebay_condition(label: Optional[str]) -> str:
    text = " ".join((label or "").lower().split())
    if not text:
        return "unknown"
    if "for parts" in text or "not working" in text:
        return "for_parts"
    if "open box" in text:
        return "new_open_box"
    if text.startswith("new"):
        return "new"
    if "like new" in text:
        return "used_like_new"
    if "excellent" in text or "very good" in text:
        return "used_excellent"
    if "good" in text or "acceptable" in text or text == "used" or "pre-owned" in text:
        return "used_good"
    return "unknown"


def _money_value(container: Any, default: float = 0.0) -> float:
    if not isinstance(container, dict):
        return default
    try:
        return float(container.get("value", default))
    except (TypeError, ValueError):
        return default


def _minimum_shipping(item: Dict[str, Any]) -> float:
    costs: list[float] = []
    for option in item.get("shippingOptions") or []:
        if not isinstance(option, dict):
            continue
        cost = option.get("shippingCost")
        if isinstance(cost, dict) and cost.get("value") is not None:
            costs.append(_money_value(cost))
    return min(costs) if costs else 0.0


def normalize_item_summary(item: Dict[str, Any]) -> SourceListing:
    price_container = item.get("price") or {}
    seller = item.get("seller") or {}
    location = item.get("itemLocation") or {}
    image = item.get("image") or {}

    listing_id = str(item.get("itemId") or "").strip()
    title = str(item.get("title") or "").strip()
    if not listing_id or not title:
        raise ValueError("eBay item summary must include itemId and title.")

    feedback_percent = seller.get("feedbackPercentage")
    feedback_score = seller.get("feedbackScore")

    return SourceListing(
        source="ebay",
        listing_id=listing_id,
        title=title,
        listing_url=item.get("itemWebUrl"),
        price=_money_value(price_container),
        currency=str(price_container.get("currency") or ""),
        shipping_price=_minimum_shipping(item),
        condition=normalize_ebay_condition(item.get("condition")),
        seller_name=seller.get("username"),
        seller_feedback_percent=float(feedback_percent) if feedback_percent is not None else None,
        seller_feedback_count=int(feedback_score) if feedback_score is not None else None,
        image_url=image.get("imageUrl"),
        item_location_country=location.get("country"),
        buying_options=list(item.get("buyingOptions") or []),
        raw_data=item,
    )


def build_search_params(
    job: SearchJob,
    search_settings: Dict[str, Any],
    config: EbayConfig,
    *,
    offset: int = 0,
    limit: Optional[int] = None,
) -> Dict[str, str]:
    max_results = int(search_settings.get("max_results_per_search", 50))
    page_limit = min(limit or max_results, max_results, 200)
    if page_limit <= 0:
        raise ValueError("Search limit must be positive.")
    if offset < 0 or offset >= 10000:
        raise ValueError("eBay Browse API offset must be between 0 and 9999.")

    filters = [
        f"price:[..{job.max_source_price:g}]",
        f"priceCurrency:{config.currency}",
    ]

    include_fixed = bool(search_settings.get("include_fixed_price", True))
    include_auctions = bool(search_settings.get("include_auctions", False))
    buying_options: list[str] = []
    if include_fixed:
        buying_options.append("FIXED_PRICE")
    if include_auctions:
        buying_options.append("AUCTION")
    if buying_options:
        filters.append("buyingOptions:{" + "|".join(buying_options) + "}")

    params = {
        "q": job.search_term,
        "limit": str(page_limit),
        "offset": str(offset),
        "filter": ",".join(filters),
    }
    return params


class EbayClient:
    def __init__(
        self,
        config: EbayConfig,
        *,
        transport: Callable[..., Any] = urlopen,
        sleeper: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.config = config
        self._transport = transport
        self._sleeper = sleeper
        self._clock = clock
        self._token: Optional[EbayAccessToken] = None

    def _decode_response(self, response: Any) -> Dict[str, Any]:
        raw = response.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        if not raw:
            return {}
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            raise EbayApiError("eBay returned a non-object JSON response.")
        return parsed

    def _decode_error(self, error: HTTPError) -> Any:
        try:
            raw = error.read()
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")
            return json.loads(raw) if raw else None
        except Exception:
            return None

    def get_access_token(self, force_refresh: bool = False) -> str:
        if not force_refresh and self._token and self._token.is_valid(self._clock()):
            return self._token.access_token

        credentials = f"{self.config.client_id}:{self.config.client_secret}".encode("utf-8")
        basic = base64.b64encode(credentials).decode("ascii")
        body = urlencode({"grant_type": "client_credentials", "scope": EBAY_SCOPE}).encode("utf-8")
        request = Request(
            self.config.token_url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
        )

        try:
            with self._transport(request, timeout=self.config.timeout_seconds) as response:
                payload = self._decode_response(response)
        except HTTPError as exc:
            raise EbayAuthError(f"eBay OAuth failed with HTTP {exc.code}.") from exc
        except URLError as exc:
            raise EbayAuthError(f"eBay OAuth network error: {exc.reason}") from exc

        access_token = str(payload.get("access_token") or "")
        expires_in = float(payload.get("expires_in") or 0)
        if not access_token or expires_in <= 0:
            raise EbayAuthError("eBay OAuth response did not contain a usable access token.")

        self._token = EbayAccessToken(
            access_token=access_token,
            expires_at=self._clock() + expires_in,
            token_type=str(payload.get("token_type") or "Application Access Token"),
        )
        return access_token

    def _headers(self, token: str) -> Dict[str, str]:
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "X-EBAY-C-MARKETPLACE-ID": self.config.marketplace_id,
        }
        if self.config.accept_language:
            headers["Accept-Language"] = self.config.accept_language
        if self.config.country_code:
            location = f"country={self.config.country_code}"
            if self.config.postal_code:
                location += f",zip={self.config.postal_code}"
            headers["X-EBAY-C-ENDUSERCTX"] = f"contextualLocation={quote(location, safe='')}"
        return headers

    def _request_json(self, path: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.config.base_url}{path}{query}"
        refreshed_after_401 = False
        last_error: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            token = self.get_access_token(force_refresh=refreshed_after_401)
            refreshed_after_401 = False
            request = Request(url, method="GET", headers=self._headers(token))
            try:
                with self._transport(request, timeout=self.config.timeout_seconds) as response:
                    return self._decode_response(response)
            except HTTPError as exc:
                payload = self._decode_error(exc)
                if exc.code == 401 and attempt < self.config.max_retries:
                    self._token = None
                    refreshed_after_401 = True
                    continue
                if exc.code == 429:
                    last_error = EbayRateLimitError("eBay rate limit reached.", exc.code, payload)
                elif 500 <= exc.code <= 599:
                    last_error = EbayApiError(f"eBay server error HTTP {exc.code}.", exc.code, payload)
                else:
                    raise EbayApiError(f"eBay API request failed with HTTP {exc.code}.", exc.code, payload) from exc
            except URLError as exc:
                last_error = EbayApiError(f"eBay API network error: {exc.reason}")

            if attempt < self.config.max_retries:
                self._sleeper(min(2 ** attempt, 8))

        assert last_error is not None
        raise last_error

    def search_job(self, job: SearchJob, search_settings: Dict[str, Any]) -> list[SourceListing]:
        max_results = min(int(search_settings.get("max_results_per_search", 50)), 10000)
        if max_results <= 0:
            return []

        results: list[SourceListing] = []
        offset = 0
        while len(results) < max_results:
            page_limit = min(200, max_results - len(results))
            params = build_search_params(job, search_settings, self.config, offset=offset, limit=page_limit)
            payload = self._request_json("/buy/browse/v1/item_summary/search", params)
            summaries = payload.get("itemSummaries") or []
            if not isinstance(summaries, list) or not summaries:
                break

            for item in summaries:
                if not isinstance(item, dict):
                    continue
                try:
                    results.append(normalize_item_summary(item))
                except ValueError:
                    continue
                if len(results) >= max_results:
                    break

            has_next = bool(payload.get("next"))
            if len(summaries) < page_limit and not has_next:
                break
            offset += len(summaries)
            if offset >= 10000:
                break

        return results


def persist_listings(
    db: DealFinderDatabase,
    listings: Iterable[SourceListing],
    job: SearchJob,
) -> list[int]:
    """Persist discovered listings using the database's marketplace/listing ID upsert."""

    ids: list[int] = []
    for listing in listings:
        context = ListingContext(
            title=listing.title,
            category=job.category,
            condition=listing.condition,
            marketplace=listing.source,
            listing_id=listing.listing_id,
            listing_url=listing.listing_url,
            brand=job.brand,
            seller_name=listing.seller_name,
            seller_feedback_percent=listing.seller_feedback_percent,
            seller_feedback_count=listing.seller_feedback_count,
            match_confidence=0.0,
            price_confidence=0.0,
        )
        ids.append(db.upsert_listing(context, listing.total_price, raw_data=listing.raw_data))
    return ids
