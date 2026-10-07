from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class DealInputs:
    purchase_price: float
    market_value: float
    condition: str
    purchase_tax_percent: Optional[float] = None
    selling_fee_percent: Optional[float] = None
    outbound_shipping: Optional[float] = None
    other_costs: Optional[float] = None


@dataclass
class DealResult:
    purchase_price: float
    raw_market_value: float
    condition_adjusted_value: float
    quick_sale_value: float
    purchase_tax: float
    landed_purchase_cost: float
    estimated_selling_fees: float
    outbound_shipping: float
    other_costs: float
    net_sale_proceeds: float
    estimated_profit: float
    roi_percent: float
    profit_margin_percent: float
    discount_to_market_percent: float
    maximum_buy_price: float
    financially_qualified: bool
    passes_purchase_price_requirement: bool
    rejection_reasons: list[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def calculate_percentage_amount(amount: float, percent: float) -> float:
    return amount * (percent / 100.0)


def calculate_purchase_tax(purchase_price: float, tax_percent: float) -> float:
    return calculate_percentage_amount(purchase_price, tax_percent)


def calculate_landed_purchase_cost(purchase_price: float, purchase_tax: float) -> float:
    return purchase_price + purchase_tax


def apply_condition_adjustment(market_value: float, condition: str, adjustments: Dict[str, float]) -> float:
    if condition not in adjustments:
        raise ValueError(f"Unknown condition: {condition}")
    return market_value * float(adjustments[condition])


def calculate_quick_sale_value(condition_adjusted_value: float, quick_sale_discount_percent: float) -> float:
    return condition_adjusted_value * (1 - quick_sale_discount_percent / 100.0)


def calculate_selling_fees(sale_price: float, fee_percent: float) -> float:
    return calculate_percentage_amount(sale_price, fee_percent)


def calculate_net_sale_proceeds(sale_price: float, selling_fees: float, outbound_shipping: float, other_costs: float) -> float:
    return sale_price - selling_fees - outbound_shipping - other_costs


def calculate_profit(net_sale_proceeds: float, landed_purchase_cost: float) -> float:
    return net_sale_proceeds - landed_purchase_cost


def calculate_roi(profit: float, landed_purchase_cost: float) -> float:
    if landed_purchase_cost <= 0:
        return 0.0
    return (profit / landed_purchase_cost) * 100.0


def calculate_profit_margin(profit: float, sale_price: float) -> float:
    if sale_price <= 0:
        return 0.0
    return (profit / sale_price) * 100.0


def calculate_discount_to_market(purchase_price: float, market_value: float) -> float:
    if market_value <= 0:
        return 0.0
    return ((market_value - purchase_price) / market_value) * 100.0


def calculate_maximum_buy_price(
    quick_sale_value: float,
    selling_fee_percent: float,
    outbound_shipping: float,
    other_costs: float,
    purchase_tax_percent: float,
    minimum_net_profit: float,
    minimum_roi_percent: float,
) -> float:
    fees = calculate_selling_fees(quick_sale_value, selling_fee_percent)
    available_after_sale_costs = quick_sale_value - fees - outbound_shipping - other_costs

    by_profit = (available_after_sale_costs - minimum_net_profit) / (1 + purchase_tax_percent / 100.0)
    roi_multiplier = 1 + minimum_roi_percent / 100.0
    by_roi = available_after_sale_costs / ((1 + purchase_tax_percent / 100.0) * roi_multiplier)

    return max(0.0, min(by_profit, by_roi))


def evaluate_deal(deal_inputs: DealInputs, strategy: Dict[str, Any]) -> DealResult:
    purchase_limits = strategy["purchase_limits"]
    profit_requirements = strategy["profit_requirements"]
    valuation = strategy["valuation"]
    costs = strategy["costs"]
    condition_cfg = strategy["condition"]

    purchase_tax_percent = (
        deal_inputs.purchase_tax_percent
        if deal_inputs.purchase_tax_percent is not None
        else float(costs.get("purchase_tax_percent", 0.0))
    ) if costs.get("include_purchase_tax", True) else 0.0

    selling_fee_percent = (
        deal_inputs.selling_fee_percent
        if deal_inputs.selling_fee_percent is not None
        else float(costs.get("default_selling_fee_percent", 0.0))
    )
    outbound_shipping = (
        deal_inputs.outbound_shipping
        if deal_inputs.outbound_shipping is not None
        else float(costs.get("default_outbound_shipping", 0.0))
    )
    other_costs = (
        deal_inputs.other_costs
        if deal_inputs.other_costs is not None
        else float(costs.get("default_other_costs", 0.0))
    )

    condition_adjusted = apply_condition_adjustment(
        deal_inputs.market_value,
        deal_inputs.condition,
        condition_cfg["resale_adjustments"],
    )
    quick_sale = calculate_quick_sale_value(
        condition_adjusted,
        float(valuation.get("quick_sale_discount_percent", 0.0)),
    )
    purchase_tax = calculate_purchase_tax(deal_inputs.purchase_price, purchase_tax_percent)
    landed = calculate_landed_purchase_cost(deal_inputs.purchase_price, purchase_tax)
    selling_fees = calculate_selling_fees(quick_sale, selling_fee_percent)
    net_proceeds = calculate_net_sale_proceeds(quick_sale, selling_fees, outbound_shipping, other_costs)
    profit = calculate_profit(net_proceeds, landed)
    roi = calculate_roi(profit, landed)
    margin = calculate_profit_margin(profit, quick_sale)
    discount = calculate_discount_to_market(deal_inputs.purchase_price, deal_inputs.market_value)
    max_buy = calculate_maximum_buy_price(
        quick_sale,
        selling_fee_percent,
        outbound_shipping,
        other_costs,
        purchase_tax_percent,
        float(profit_requirements["minimum_net_profit"]),
        float(profit_requirements["minimum_roi_percent"]),
    )

    min_purchase = float(purchase_limits.get("minimum_purchase_price", 0.0))
    max_purchase = float(purchase_limits.get("maximum_purchase_price", float("inf")))
    passes_purchase = min_purchase <= deal_inputs.purchase_price <= max_purchase

    reasons: list[str] = []
    if not passes_purchase:
        reasons.append("purchase_price_outside_allowed_range")
    if profit < float(profit_requirements["minimum_net_profit"]):
        reasons.append("net_profit_below_minimum")
    if roi < float(profit_requirements["minimum_roi_percent"]):
        reasons.append("roi_below_minimum")
    if margin < float(profit_requirements["minimum_profit_margin_percent"]):
        reasons.append("profit_margin_below_minimum")
    if discount < float(profit_requirements["minimum_discount_to_market_percent"]):
        reasons.append("discount_to_market_below_minimum")

    return DealResult(
        purchase_price=deal_inputs.purchase_price,
        raw_market_value=deal_inputs.market_value,
        condition_adjusted_value=condition_adjusted,
        quick_sale_value=quick_sale,
        purchase_tax=purchase_tax,
        landed_purchase_cost=landed,
        estimated_selling_fees=selling_fees,
        outbound_shipping=outbound_shipping,
        other_costs=other_costs,
        net_sale_proceeds=net_proceeds,
        estimated_profit=profit,
        roi_percent=roi,
        profit_margin_percent=margin,
        discount_to_market_percent=discount,
        maximum_buy_price=max_buy,
        financially_qualified=(len(reasons) == 0),
        passes_purchase_price_requirement=passes_purchase,
        rejection_reasons=reasons,
    )
