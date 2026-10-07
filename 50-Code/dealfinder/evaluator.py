from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from .calculator import DealInputs, DealResult, evaluate_deal


@dataclass
class ListingContext:
    title: str
    category: str
    condition: str
    marketplace: str = ""
    listing_id: Optional[str] = None
    listing_url: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    seller_name: Optional[str] = None
    seller_feedback_percent: Optional[float] = None
    seller_feedback_count: Optional[int] = None
    match_confidence: float = 0.0
    price_confidence: float = 0.0
    description: str = ""
    possible_counterfeit: bool = False
    unusually_high_market_value: bool = False
    price_is_extremely_low: bool = False


@dataclass
class EvaluationResult:
    title: str
    financial_result: DealResult
    category_allowed: bool
    condition_allowed: bool
    passes_match_confidence: bool
    passes_price_confidence: bool
    passes_seller_quality: bool
    risky_keywords_found: list[str] = field(default_factory=list)
    rejection_reasons: list[str] = field(default_factory=list)
    manual_review_reasons: list[str] = field(default_factory=list)
    hard_rejected: bool = False
    requires_manual_review: bool = False
    qualified_for_scoring: bool = False
    status: str = "reject"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def normalize_text(value: Optional[str]) -> str:
    return " ".join((value or "").lower().strip().split())


def combine_listing_text(listing: ListingContext) -> str:
    return normalize_text(f"{listing.title} {listing.description}")


def find_risky_keywords(listing: ListingContext, strategy: Dict[str, Any]) -> list[str]:
    text = combine_listing_text(listing)
    matches: list[str] = []
    for phrase in strategy.get("risk_filters", {}).get("reject_phrases", []):
        if normalize_text(phrase) in text:
            matches.append(phrase)
    return matches


def is_category_allowed(category: str, strategy: Dict[str, Any]) -> bool:
    categories = strategy.get("categories", {})
    if category in categories.get("disabled", []):
        return False
    enabled = categories.get("enabled", [])
    return not enabled or category in enabled


def is_condition_allowed(condition: str, strategy: Dict[str, Any]) -> bool:
    cfg = strategy.get("condition", {})
    return condition in cfg.get("allowed", []) and condition not in cfg.get("excluded", [])


def passes_match_confidence(value: float, strategy: Dict[str, Any]) -> bool:
    return value >= float(strategy.get("matching", {}).get("minimum_match_confidence", 0.0))


def passes_price_confidence(value: float, strategy: Dict[str, Any]) -> bool:
    minimum = float(strategy.get("valuation", {}).get("minimum_price_confidence", 70.0))
    return value >= minimum


def evaluate_seller_quality(
    listing: ListingContext,
    minimum_feedback_percent: float = 95.0,
    minimum_feedback_count: int = 5,
) -> bool:
    if listing.seller_feedback_percent is None or listing.seller_feedback_count is None:
        return False
    return (
        listing.seller_feedback_percent >= minimum_feedback_percent
        and listing.seller_feedback_count >= minimum_feedback_count
    )


def build_manual_review_reasons(listing: ListingContext, match_ok: bool, price_ok: bool, seller_ok: bool) -> list[str]:
    reasons: list[str] = []
    if not match_ok:
        reasons.append("poor_product_match")
    if not price_ok:
        reasons.append("low_price_confidence")
    if not seller_ok:
        reasons.append("seller_has_low_or_missing_feedback")
    if not listing.model:
        reasons.append("missing_model_number")
    if not listing.condition:
        reasons.append("missing_condition")
    if listing.price_is_extremely_low:
        reasons.append("price_is_extremely_low")
    if listing.unusually_high_market_value:
        reasons.append("unusually_high_market_value")
    return reasons


def evaluate_opportunity(deal_inputs: DealInputs, listing: ListingContext, strategy: Dict[str, Any]) -> EvaluationResult:
    financial = evaluate_deal(deal_inputs, strategy)
    category_ok = is_category_allowed(listing.category, strategy)
    condition_ok = is_condition_allowed(listing.condition, strategy)
    match_ok = passes_match_confidence(listing.match_confidence, strategy)
    price_ok = passes_price_confidence(listing.price_confidence, strategy)
    seller_ok = evaluate_seller_quality(listing)
    risky = find_risky_keywords(listing, strategy)

    rejection_reasons = list(financial.rejection_reasons)
    if not category_ok:
        rejection_reasons.append("category_not_allowed")
    if not condition_ok:
        rejection_reasons.append("condition_not_allowed")
    if risky:
        rejection_reasons.append("risky_keywords_found")
    if listing.possible_counterfeit:
        rejection_reasons.append("possible_counterfeit")

    hard_rejected = bool(rejection_reasons)
    manual_reasons = build_manual_review_reasons(listing, match_ok, price_ok, seller_ok)
    requires_review = bool(manual_reasons) and not hard_rejected
    qualified = not hard_rejected
    status = "reject" if hard_rejected else ("investigate" if requires_review else "qualified")

    return EvaluationResult(
        title=listing.title,
        financial_result=financial,
        category_allowed=category_ok,
        condition_allowed=condition_ok,
        passes_match_confidence=match_ok,
        passes_price_confidence=price_ok,
        passes_seller_quality=seller_ok,
        risky_keywords_found=risky,
        rejection_reasons=rejection_reasons,
        manual_review_reasons=manual_reasons,
        hard_rejected=hard_rejected,
        requires_manual_review=requires_review,
        qualified_for_scoring=qualified,
        status=status,
    )


def print_evaluation_result(result: EvaluationResult) -> None:
    print(f"{result.title}: {result.status}")
    print(f"Profit: ${result.financial_result.estimated_profit:.2f}")
    print(f"ROI: {result.financial_result.roi_percent:.1f}%")
