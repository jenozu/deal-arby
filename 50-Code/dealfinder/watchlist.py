from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


@dataclass
class WatchlistProduct:
    id: str
    enabled: bool
    name: str
    brand: str
    category: str
    product_type: str
    model_numbers: List[str]
    search_terms: List[str]
    exclude_terms: List[str]
    preferred_conditions: List[str]
    max_source_price: Optional[float] = None
    manual_review_required: bool = False
    notes: str = ""


@dataclass
class SearchSource:
    source: str
    enabled: bool
    priority: int


@dataclass
class SearchJob:
    source: str
    source_priority: int
    product_id: str
    product_name: str
    brand: str
    category: str
    product_type: str
    search_term: str
    max_source_price: float
    preferred_conditions: List[str]
    exclude_terms: List[str]
    manual_review_required: bool


def normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").lower().strip().split())


def load_watchlist_config(path: str = "config/watchlist.yaml") -> Dict[str, Any]:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Watchlist file not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise ValueError("watchlist.yaml must contain a YAML dictionary.")
    validate_watchlist_config(data)
    return data


def validate_watchlist_config(config: Dict[str, Any]) -> None:
    for key in ["watchlist", "search_settings", "listing_filters", "source_priority"]:
        if key not in config:
            raise ValueError(f"Missing required watchlist section: {key}")
    if not isinstance(config["watchlist"], list):
        raise ValueError("'watchlist' must be a list.")

    seen_ids = set()
    required = ["id", "enabled", "name", "brand", "category", "product_type", "model_numbers", "search_terms", "exclude_terms", "preferred_conditions"]
    for index, product in enumerate(config["watchlist"]):
        if not isinstance(product, dict):
            raise ValueError(f"Watchlist item {index} must be a dictionary.")
        for field_name in required:
            if field_name not in product:
                raise ValueError(f"Product at index {index} is missing required field '{field_name}'.")
        product_id = product["id"]
        if not isinstance(product_id, str) or not product_id.strip():
            raise ValueError(f"Product at index {index} has an invalid ID.")
        if product_id in seen_ids:
            raise ValueError(f"Duplicate watchlist product ID: {product_id}")
        seen_ids.add(product_id)
        if not isinstance(product["search_terms"], list):
            raise ValueError(f"{product_id}.search_terms must be a list.")
        if product["enabled"] and not product["search_terms"]:
            raise ValueError(f"Enabled product '{product_id}' must have at least one search term.")
        max_price = product.get("max_source_price")
        if max_price is not None and max_price < 0:
            raise ValueError(f"{product_id}.max_source_price cannot be negative.")

    settings = config["search_settings"]
    if settings.get("global_max_source_price", 0) < 0:
        raise ValueError("global_max_source_price cannot be negative.")
    if settings.get("max_results_per_search", 0) <= 0:
        raise ValueError("max_results_per_search must be greater than 0.")

    sources = config["source_priority"]
    if not isinstance(sources, list):
        raise ValueError("'source_priority' must be a list.")
    seen_sources = set()
    for source in sources:
        if "source" not in source:
            raise ValueError("Every source must contain a 'source' field.")
        if source["source"] in seen_sources:
            raise ValueError(f"Duplicate source configured: {source['source']}")
        seen_sources.add(source["source"])


def product_from_dict(product: Dict[str, Any]) -> WatchlistProduct:
    return WatchlistProduct(
        id=product["id"], enabled=bool(product["enabled"]), name=product["name"], brand=product["brand"],
        category=product["category"], product_type=product["product_type"], model_numbers=list(product.get("model_numbers", [])),
        search_terms=list(product.get("search_terms", [])), exclude_terms=list(product.get("exclude_terms", [])),
        preferred_conditions=list(product.get("preferred_conditions", [])), max_source_price=product.get("max_source_price"),
        manual_review_required=bool(product.get("manual_review_required", False)), notes=product.get("notes", ""),
    )


def get_products(config: Dict[str, Any]) -> List[WatchlistProduct]:
    return [product_from_dict(p) for p in config["watchlist"]]


def get_enabled_products(config: Dict[str, Any]) -> List[WatchlistProduct]:
    return [p for p in get_products(config) if p.enabled]


def get_product_by_id(config: Dict[str, Any], product_id: str) -> Optional[WatchlistProduct]:
    return next((p for p in get_products(config) if p.id == product_id), None)


def get_sources(config: Dict[str, Any]) -> List[SearchSource]:
    return [SearchSource(s["source"], bool(s.get("enabled", False)), int(s.get("priority", 999))) for s in config["source_priority"]]


def get_enabled_sources(config: Dict[str, Any]) -> List[SearchSource]:
    return sorted([s for s in get_sources(config) if s.enabled], key=lambda s: s.priority)


def get_effective_max_source_price(product: WatchlistProduct, config: Dict[str, Any]) -> float:
    global_max = float(config["search_settings"]["global_max_source_price"])
    return global_max if product.max_source_price is None else min(float(product.max_source_price), global_max)


def price_is_allowed(price: float, product: WatchlistProduct, config: Dict[str, Any]) -> bool:
    return 0 <= price <= get_effective_max_source_price(product, config)


def get_global_exclude_terms(config: Dict[str, Any]) -> List[str]:
    return config["listing_filters"].get("exclude_global_terms", [])


def find_excluded_terms(title: str, product: WatchlistProduct, config: Dict[str, Any]) -> List[str]:
    normalized = normalize_text(title)
    matches, seen = [], set()
    for term in get_global_exclude_terms(config) + product.exclude_terms:
        n = normalize_text(term)
        if n and n in normalized and n not in seen:
            matches.append(term)
            seen.add(n)
    return matches


def title_passes_basic_filters(title: str, product: WatchlistProduct, config: Dict[str, Any]) -> bool:
    filters = config["listing_filters"]
    normalized = normalize_text(title)
    if filters.get("require_title", True) and not normalized:
        return False
    if len(normalized) < int(filters.get("minimum_title_length", 0)):
        return False
    return not find_excluded_terms(title, product, config)


def title_contains_brand(title: str, product: WatchlistProduct) -> bool:
    brand = normalize_text(product.brand)
    return True if not brand else brand in normalize_text(title)


def find_matching_model_numbers(title: str, product: WatchlistProduct) -> List[str]:
    normalized = normalize_text(title)
    return [m for m in product.model_numbers if normalize_text(m) and normalize_text(m) in normalized]


def has_exact_model_match(title: str, product: WatchlistProduct) -> bool:
    return bool(product.model_numbers and find_matching_model_numbers(title, product))


def build_search_jobs(config: Dict[str, Any]) -> List[SearchJob]:
    jobs: list[SearchJob] = []
    for source in get_enabled_sources(config):
        for product in get_enabled_products(config):
            max_price = get_effective_max_source_price(product, config)
            for term in product.search_terms:
                jobs.append(SearchJob(
                    source=source.source, source_priority=source.priority, product_id=product.id, product_name=product.name,
                    brand=product.brand, category=product.category, product_type=product.product_type, search_term=term,
                    max_source_price=max_price, preferred_conditions=list(product.preferred_conditions),
                    exclude_terms=list(product.exclude_terms), manual_review_required=product.manual_review_required,
                ))
    return jobs


def get_search_jobs_for_source(config: Dict[str, Any], source_name: str) -> List[SearchJob]:
    n = normalize_text(source_name)
    return [job for job in build_search_jobs(config) if normalize_text(job.source) == n]


def get_search_jobs_for_product(config: Dict[str, Any], product_id: str) -> List[SearchJob]:
    return [job for job in build_search_jobs(config) if job.product_id == product_id]


def listing_passes_watchlist_filters(title: str, price: float, product: WatchlistProduct, config: Dict[str, Any]) -> bool:
    return price_is_allowed(price, product, config) and title_passes_basic_filters(title, product, config)


def explain_listing_filter(title: str, price: float, product: WatchlistProduct, config: Dict[str, Any]) -> Dict[str, Any]:
    price_allowed = price_is_allowed(price, product, config)
    excluded = find_excluded_terms(title, product, config)
    title_allowed = title_passes_basic_filters(title, product, config)
    return {
        "passes": price_allowed and title_allowed,
        "price_allowed": price_allowed,
        "title_allowed": title_allowed,
        "excluded_terms": excluded,
        "brand_match": title_contains_brand(title, product),
        "exact_model_match": has_exact_model_match(title, product),
        "effective_max_source_price": get_effective_max_source_price(product, config),
    }


def get_watchlist_summary(config: Dict[str, Any]) -> Dict[str, Any]:
    all_products = get_products(config)
    enabled = get_enabled_products(config)
    category_counts: Dict[str, int] = {}
    for product in enabled:
        category_counts[product.category] = category_counts.get(product.category, 0) + 1
    return {
        "total_products": len(all_products), "enabled_products": len(enabled),
        "enabled_sources": len(get_enabled_sources(config)), "search_jobs": len(build_search_jobs(config)),
        "categories": category_counts,
    }
