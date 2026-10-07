import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from .calculator import DealResult
from .evaluator import EvaluationResult, ListingContext
from .scoring import OpportunityScore


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class DealFinderDatabase:
    def __init__(self, database_path: str = "data/deal_finder.db") -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize_database()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize_database(self) -> None:
        with self.connection() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    marketplace TEXT NOT NULL,
                    listing_id TEXT,
                    listing_url TEXT,
                    title TEXT NOT NULL,
                    brand TEXT,
                    model TEXT,
                    category TEXT,
                    condition TEXT,
                    seller_name TEXT,
                    seller_feedback_percent REAL,
                    seller_feedback_count INTEGER,
                    purchase_price REAL,
                    match_confidence REAL,
                    price_confidence REAL,
                    first_seen TEXT NOT NULL,
                    last_seen TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    raw_data_json TEXT,
                    UNIQUE(marketplace, listing_id)
                );

                CREATE TABLE IF NOT EXISTS opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_db_id INTEGER NOT NULL UNIQUE,
                    raw_market_value REAL,
                    condition_adjusted_value REAL,
                    quick_sale_value REAL,
                    purchase_tax REAL,
                    landed_purchase_cost REAL,
                    estimated_selling_fees REAL,
                    outbound_shipping REAL,
                    other_costs REAL,
                    net_sale_proceeds REAL,
                    estimated_profit REAL,
                    roi_percent REAL,
                    profit_margin_percent REAL,
                    discount_to_market_percent REAL,
                    maximum_buy_price REAL,
                    financially_qualified INTEGER,
                    hard_rejected INTEGER,
                    requires_manual_review INTEGER,
                    qualified_for_scoring INTEGER,
                    evaluation_status TEXT,
                    total_score REAL,
                    rating TEXT,
                    rejection_reasons_json TEXT,
                    manual_review_reasons_json TEXT,
                    score_breakdown_json TEXT,
                    first_scored TEXT NOT NULL,
                    last_scored TEXT NOT NULL,
                    opportunity_status TEXT NOT NULL DEFAULT 'new',
                    FOREIGN KEY(listing_db_id) REFERENCES listings(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS price_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_db_id INTEGER,
                    product_key TEXT NOT NULL,
                    marketplace TEXT NOT NULL,
                    observed_price REAL NOT NULL,
                    shipping_price REAL NOT NULL DEFAULT 0,
                    total_price REAL NOT NULL,
                    condition TEXT,
                    observed_at TEXT NOT NULL,
                    source_url TEXT,
                    FOREIGN KEY(listing_db_id) REFERENCES listings(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    listing_db_id INTEGER NOT NULL,
                    opportunity_id INTEGER,
                    alert_type TEXT NOT NULL,
                    destination TEXT,
                    sent_at TEXT NOT NULL,
                    success INTEGER NOT NULL DEFAULT 1,
                    error_message TEXT,
                    FOREIGN KEY(listing_db_id) REFERENCES listings(id) ON DELETE CASCADE,
                    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id) ON DELETE SET NULL
                );

                CREATE INDEX IF NOT EXISTS idx_listings_marketplace ON listings(marketplace);
                CREATE INDEX IF NOT EXISTS idx_listings_last_seen ON listings(last_seen);
                CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(total_score);
                CREATE INDEX IF NOT EXISTS idx_opportunities_status ON opportunities(opportunity_status);
                CREATE INDEX IF NOT EXISTS idx_price_product ON price_observations(product_key);
                CREATE INDEX IF NOT EXISTS idx_price_observed_at ON price_observations(observed_at);
                CREATE INDEX IF NOT EXISTS idx_alerts_listing ON alerts(listing_db_id);
                """
            )

    @staticmethod
    def _bool_to_int(value: bool) -> int:
        return 1 if value else 0

    @staticmethod
    def _row_to_dict(row: Optional[sqlite3.Row]) -> Optional[Dict[str, Any]]:
        return dict(row) if row is not None else None

    @staticmethod
    def _json_dumps(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    def get_listing(self, marketplace: str, listing_id: str) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT * FROM listings WHERE marketplace=? AND listing_id=?",
                (marketplace, listing_id),
            ).fetchone()
        return self._row_to_dict(row)

    def get_listing_by_db_id(self, listing_db_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM listings WHERE id=?", (listing_db_id,)).fetchone()
        return self._row_to_dict(row)

    def listing_exists(self, marketplace: str, listing_id: str) -> bool:
        return self.get_listing(marketplace, listing_id) is not None

    def upsert_listing(self, listing: ListingContext, purchase_price: float, raw_data: Any = None) -> int:
        if not listing.marketplace:
            raise ValueError("listing.marketplace is required")
        if not listing.listing_id:
            raise ValueError("listing.listing_id is required")
        now = utc_now_iso()
        raw_json = self._json_dumps(raw_data) if raw_data is not None else None
        with self.connection() as conn:
            existing = conn.execute(
                "SELECT id FROM listings WHERE marketplace=? AND listing_id=?",
                (listing.marketplace, listing.listing_id),
            ).fetchone()
            if existing:
                listing_db_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE listings SET listing_url=?, title=?, brand=?, model=?, category=?, condition=?,
                        seller_name=?, seller_feedback_percent=?, seller_feedback_count=?, purchase_price=?,
                        match_confidence=?, price_confidence=?, last_seen=?, active=1, raw_data_json=?
                    WHERE id=?
                    """,
                    (
                        listing.listing_url, listing.title, listing.brand, listing.model, listing.category,
                        listing.condition, listing.seller_name, listing.seller_feedback_percent,
                        listing.seller_feedback_count, purchase_price, listing.match_confidence,
                        listing.price_confidence, now, raw_json, listing_db_id,
                    ),
                )
                return listing_db_id
            cur = conn.execute(
                """
                INSERT INTO listings (
                    marketplace, listing_id, listing_url, title, brand, model, category, condition,
                    seller_name, seller_feedback_percent, seller_feedback_count, purchase_price,
                    match_confidence, price_confidence, first_seen, last_seen, active, raw_data_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    listing.marketplace, listing.listing_id, listing.listing_url, listing.title,
                    listing.brand, listing.model, listing.category, listing.condition, listing.seller_name,
                    listing.seller_feedback_percent, listing.seller_feedback_count, purchase_price,
                    listing.match_confidence, listing.price_confidence, now, now, raw_json,
                ),
            )
            return int(cur.lastrowid)

    def save_opportunity(
        self,
        listing_db_id: int,
        financial: DealResult,
        evaluation: EvaluationResult,
        score: OpportunityScore,
    ) -> int:
        now = utc_now_iso()
        breakdown_json = self._json_dumps(asdict(score.breakdown))
        rejection_json = self._json_dumps(evaluation.rejection_reasons)
        manual_json = self._json_dumps(evaluation.manual_review_reasons)
        values = (
            financial.raw_market_value, financial.condition_adjusted_value, financial.quick_sale_value,
            financial.purchase_tax, financial.landed_purchase_cost, financial.estimated_selling_fees,
            financial.outbound_shipping, financial.other_costs, financial.net_sale_proceeds,
            financial.estimated_profit, financial.roi_percent, financial.profit_margin_percent,
            financial.discount_to_market_percent, financial.maximum_buy_price,
            self._bool_to_int(financial.financially_qualified), self._bool_to_int(evaluation.hard_rejected),
            self._bool_to_int(evaluation.requires_manual_review), self._bool_to_int(evaluation.qualified_for_scoring),
            evaluation.status, score.total_score, score.rating, rejection_json, manual_json, breakdown_json,
        )
        with self.connection() as conn:
            existing = conn.execute("SELECT id FROM opportunities WHERE listing_db_id=?", (listing_db_id,)).fetchone()
            if existing:
                opportunity_id = int(existing["id"])
                conn.execute(
                    """
                    UPDATE opportunities SET
                        raw_market_value=?, condition_adjusted_value=?, quick_sale_value=?, purchase_tax=?,
                        landed_purchase_cost=?, estimated_selling_fees=?, outbound_shipping=?, other_costs=?,
                        net_sale_proceeds=?, estimated_profit=?, roi_percent=?, profit_margin_percent=?,
                        discount_to_market_percent=?, maximum_buy_price=?, financially_qualified=?,
                        hard_rejected=?, requires_manual_review=?, qualified_for_scoring=?, evaluation_status=?,
                        total_score=?, rating=?, rejection_reasons_json=?, manual_review_reasons_json=?,
                        score_breakdown_json=?, last_scored=?
                    WHERE id=?
                    """,
                    values + (now, opportunity_id),
                )
                return opportunity_id
            cur = conn.execute(
                """
                INSERT INTO opportunities (
                    listing_db_id, raw_market_value, condition_adjusted_value, quick_sale_value, purchase_tax,
                    landed_purchase_cost, estimated_selling_fees, outbound_shipping, other_costs,
                    net_sale_proceeds, estimated_profit, roi_percent, profit_margin_percent,
                    discount_to_market_percent, maximum_buy_price, financially_qualified, hard_rejected,
                    requires_manual_review, qualified_for_scoring, evaluation_status, total_score, rating,
                    rejection_reasons_json, manual_review_reasons_json, score_breakdown_json,
                    first_scored, last_scored
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (listing_db_id,) + values + (now, now),
            )
            return int(cur.lastrowid)

    def get_opportunity(self, listing_db_id: int) -> Optional[Dict[str, Any]]:
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM opportunities WHERE listing_db_id=?", (listing_db_id,)).fetchone()
        return self._row_to_dict(row)

    def update_opportunity_status(self, listing_db_id: int, status: str) -> None:
        allowed = {"new", "investigate", "watching", "purchased", "passed", "expired", "sold"}
        if status not in allowed:
            raise ValueError(f"Invalid opportunity status: {status}")
        with self.connection() as conn:
            conn.execute("UPDATE opportunities SET opportunity_status=? WHERE listing_db_id=?", (status, listing_db_id))

    def add_price_observation(
        self,
        product_key: str,
        marketplace: str,
        observed_price: float,
        shipping_price: float = 0.0,
        condition: Optional[str] = None,
        source_url: Optional[str] = None,
        listing_db_id: Optional[int] = None,
    ) -> int:
        if observed_price < 0 or shipping_price < 0:
            raise ValueError("Prices cannot be negative")
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO price_observations (
                    listing_db_id, product_key, marketplace, observed_price, shipping_price,
                    total_price, condition, observed_at, source_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing_db_id, product_key, marketplace, observed_price, shipping_price,
                    observed_price + shipping_price, condition, utc_now_iso(), source_url,
                ),
            )
            return int(cur.lastrowid)

    def get_price_history(self, product_key: str, limit: int = 100) -> list[Dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM price_observations WHERE product_key=? ORDER BY observed_at DESC, id DESC LIMIT ?",
                (product_key, limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def record_alert(
        self,
        listing_db_id: int,
        alert_type: str,
        destination: Optional[str] = None,
        opportunity_id: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> int:
        with self.connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO alerts (listing_db_id, opportunity_id, alert_type, destination, sent_at, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (listing_db_id, opportunity_id, alert_type, destination, utc_now_iso(), self._bool_to_int(success), error_message),
            )
            return int(cur.lastrowid)

    def has_successful_alert(self, listing_db_id: int, alert_type: Optional[str] = None) -> bool:
        query = "SELECT 1 FROM alerts WHERE listing_db_id=? AND success=1"
        args: list[Any] = [listing_db_id]
        if alert_type is not None:
            query += " AND alert_type=?"
            args.append(alert_type)
        query += " LIMIT 1"
        with self.connection() as conn:
            return conn.execute(query, args).fetchone() is not None

    def get_top_opportunities(self, limit: int = 25, minimum_score: float = 0, active_only: bool = True) -> list[Dict[str, Any]]:
        query = """
            SELECT o.*, l.marketplace, l.listing_id, l.listing_url, l.title, l.purchase_price, l.active
            FROM opportunities o JOIN listings l ON l.id=o.listing_db_id
            WHERE o.total_score >= ?
        """
        args: list[Any] = [minimum_score]
        if active_only:
            query += " AND l.active=1"
        query += " ORDER BY o.total_score DESC, o.estimated_profit DESC LIMIT ?"
        args.append(limit)
        with self.connection() as conn:
            rows = conn.execute(query, args).fetchall()
        return [dict(row) for row in rows]

    def mark_listing_inactive(self, listing_db_id: int) -> None:
        with self.connection() as conn:
            conn.execute("UPDATE listings SET active=0 WHERE id=?", (listing_db_id,))

    def get_statistics(self) -> Dict[str, int]:
        with self.connection() as conn:
            listing_count = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
            opportunity_count = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
            observation_count = conn.execute("SELECT COUNT(*) FROM price_observations").fetchone()[0]
            alert_count = conn.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
        return {
            "listings": listing_count,
            "opportunities": opportunity_count,
            "price_observations": observation_count,
            "alerts": alert_count,
        }


if __name__ == "__main__":
    db = DealFinderDatabase()
    print(db.get_statistics())
