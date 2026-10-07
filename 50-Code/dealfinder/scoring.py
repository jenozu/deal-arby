from dataclasses import asdict, dataclass
from typing import Any, Dict

from .evaluator import EvaluationResult, ListingContext


@dataclass
class ScoreBreakdown:
    roi_score: float
    roi_points: float
    net_profit_score: float
    net_profit_points: float
    discount_score: float
    discount_points: float
    price_confidence_score: float
    price_confidence_points: float
    match_confidence_score: float
    match_confidence_points: float
    condition_score: float
    condition_points: float
    seller_quality_score: float
    seller_quality_points: float


@dataclass
class OpportunityScore:
    title: str
    total_score: float
    rating: str
    breakdown: ScoreBreakdown
    financially_qualified: bool
    hard_rejected: bool
    requires_manual_review: bool
    qualified_for_scoring: bool
    estimated_profit: float
    roi_percent: float
    quick_sale_value: float
    maximum_buy_price: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def weighted_points(score: float, weight: float) -> float:
    return clamp(score) * weight / 100.0


def _scaled(value: float, minimum: float) -> float:
    if minimum <= 0:
        return 100.0
    if value <= 0:
        return 0.0
    if value < minimum:
        return clamp((value / minimum) * 50.0)
    return clamp(50.0 + ((value - minimum) / minimum) * 50.0)


def score_roi(value: float, minimum: float) -> float:
    return _scaled(value, minimum)


def score_net_profit(value: float, minimum: float) -> float:
    if minimum <= 0:
        return 100.0
    if value < minimum:
        return clamp((value / minimum) * 50.0)
    if value < minimum * 2:
        return 50.0 + ((value - minimum) / minimum) * 25.0
    if value < minimum * 3:
        return 75.0 + ((value - minimum * 2) / minimum) * 25.0
    return 100.0


def score_discount_to_market(value: float, minimum: float) -> float:
    return _scaled(value, minimum)


def score_price_confidence(value: float) -> float:
    return clamp(value)


def score_match_confidence(value: float) -> float:
    return clamp(value)


def score_condition(condition: str, strategy: Dict[str, Any]) -> float:
    multiplier = float(strategy.get("condition", {}).get("resale_adjustments", {}).get(condition, 0.0))
    return clamp(multiplier * 100.0)


def score_seller_quality(listing: ListingContext) -> float:
    if listing.seller_feedback_percent is None or listing.seller_feedback_count is None:
        return 70.0
    percent_score = clamp(listing.seller_feedback_percent)
    volume_score = clamp((listing.seller_feedback_count / 100.0) * 100.0)
    return percent_score * 0.7 + volume_score * 0.3


def classify_score(total: float, strategy: Dict[str, Any]) -> str:
    thresholds = strategy["scoring"]["thresholds"]
    for label in ("exceptional", "strong", "investigate", "weak"):
        if total >= float(thresholds[label]):
            return label
    return "reject"


def validate_scoring_weights(strategy: Dict[str, Any]) -> None:
    weights = strategy["scoring"]["weights"]
    if abs(sum(float(v) for v in weights.values()) - 100.0) > 1e-9:
        raise ValueError("Scoring weights must sum to 100.")


def calculate_opportunity_score(evaluation: EvaluationResult, listing: ListingContext, strategy: Dict[str, Any]) -> OpportunityScore:
    validate_scoring_weights(strategy)
    financial = evaluation.financial_result
    weights = strategy["scoring"]["weights"]
    mins = strategy["profit_requirements"]

    raw = {
        "roi": score_roi(financial.roi_percent, float(mins["minimum_roi_percent"])),
        "net_profit": score_net_profit(financial.estimated_profit, float(mins["minimum_net_profit"])),
        "discount_to_market": score_discount_to_market(financial.discount_to_market_percent, float(mins["minimum_discount_to_market_percent"])),
        "price_confidence": score_price_confidence(listing.price_confidence),
        "match_confidence": score_match_confidence(listing.match_confidence),
        "condition": score_condition(listing.condition, strategy),
        "seller_quality": score_seller_quality(listing),
    }
    points = {k: weighted_points(raw[k], float(weights[k])) for k in raw}

    if evaluation.hard_rejected:
        total = 0.0
        rating = "reject"
    else:
        total = round(sum(points.values()), 2)
        rating = classify_score(total, strategy)

    breakdown = ScoreBreakdown(
        roi_score=raw["roi"], roi_points=points["roi"],
        net_profit_score=raw["net_profit"], net_profit_points=points["net_profit"],
        discount_score=raw["discount_to_market"], discount_points=points["discount_to_market"],
        price_confidence_score=raw["price_confidence"], price_confidence_points=points["price_confidence"],
        match_confidence_score=raw["match_confidence"], match_confidence_points=points["match_confidence"],
        condition_score=raw["condition"], condition_points=points["condition"],
        seller_quality_score=raw["seller_quality"], seller_quality_points=points["seller_quality"],
    )
    return OpportunityScore(
        title=listing.title,
        total_score=total,
        rating=rating,
        breakdown=breakdown,
        financially_qualified=financial.financially_qualified,
        hard_rejected=evaluation.hard_rejected,
        requires_manual_review=evaluation.requires_manual_review,
        qualified_for_scoring=evaluation.qualified_for_scoring,
        estimated_profit=financial.estimated_profit,
        roi_percent=financial.roi_percent,
        quick_sale_value=financial.quick_sale_value,
        maximum_buy_price=financial.maximum_buy_price,
    )


def qualifies_for_alert(score: OpportunityScore, evaluation: EvaluationResult, listing: ListingContext, strategy: Dict[str, Any]) -> bool:
    cfg = strategy.get("alerts", {})
    if not cfg.get("enabled", False) or evaluation.hard_rejected:
        return False
    return (
        score.total_score >= float(cfg.get("minimum_score", 0))
        and score.estimated_profit >= float(cfg.get("minimum_profit", 0))
        and score.roi_percent >= float(cfg.get("minimum_roi_percent", 0))
        and listing.match_confidence >= float(cfg.get("minimum_match_confidence", 0))
    )


def print_opportunity_score(score: OpportunityScore) -> None:
    print(f"{score.title}: {score.total_score:.1f}/100 ({score.rating})")
