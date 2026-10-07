from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional


@dataclass
class SourceListing:
    """Marketplace-neutral listing returned by a source connector."""

    source: str
    listing_id: str
    title: str
    listing_url: Optional[str]
    price: float
    currency: str
    shipping_price: float = 0.0
    condition: str = "unknown"
    seller_name: Optional[str] = None
    seller_feedback_percent: Optional[float] = None
    seller_feedback_count: Optional[int] = None
    image_url: Optional[str] = None
    item_location_country: Optional[str] = None
    buying_options: list[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_price(self) -> float:
        return self.price + self.shipping_price

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_price"] = self.total_price
        return data
