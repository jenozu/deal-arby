from dealfinder.calculator import DealInputs
from dealfinder.database import DealFinderDatabase
from dealfinder.evaluator import ListingContext, evaluate_opportunity
from dealfinder.scoring import calculate_opportunity_score


def make_listing(listing_id="EBAY-1"):
    return ListingContext(
        title="Sony WH-1000XM5", category="electronics", condition="used_excellent",
        marketplace="ebay", listing_id=listing_id, model="WH-1000XM5",
        seller_feedback_percent=99.5, seller_feedback_count=100,
        match_confidence=98, price_confidence=92,
    )


def test_database_initializes(tmp_path):
    db = DealFinderDatabase(str(tmp_path / "db.sqlite"))
    assert db.get_statistics() == {"listings": 0, "opportunities": 0, "price_observations": 0, "alerts": 0}


def test_listing_upsert_deduplicates(tmp_path):
    db = DealFinderDatabase(str(tmp_path / "db.sqlite"))
    listing = make_listing()
    first = db.upsert_listing(listing, 30)
    second = db.upsert_listing(listing, 35)
    assert first == second
    assert db.get_statistics()["listings"] == 1
    assert db.get_listing("ebay", "EBAY-1")["purchase_price"] == 35


def test_save_opportunity(tmp_path, strategy):
    db = DealFinderDatabase(str(tmp_path / "db.sqlite"))
    listing = make_listing()
    listing_db_id = db.upsert_listing(listing, 30)
    evaluation = evaluate_opportunity(DealInputs(30, 180, "used_excellent"), listing, strategy)
    score = calculate_opportunity_score(evaluation, listing, strategy)
    opportunity_id = db.save_opportunity(listing_db_id, evaluation.financial_result, evaluation, score)
    assert opportunity_id > 0
    assert db.get_opportunity(listing_db_id)["total_score"] == score.total_score


def test_price_history_and_alerts(tmp_path):
    db = DealFinderDatabase(str(tmp_path / "db.sqlite"))
    listing_id = db.upsert_listing(make_listing(), 30)
    db.add_price_observation("sony_wh1000xm5", "ebay", 100, 10, listing_db_id=listing_id)
    assert db.get_price_history("sony_wh1000xm5")[0]["total_price"] == 110
    db.record_alert(listing_id, "email", "test@example.com")
    assert db.has_successful_alert(listing_id, "email") is True


def test_mark_inactive(tmp_path):
    db = DealFinderDatabase(str(tmp_path / "db.sqlite"))
    listing_id = db.upsert_listing(make_listing(), 30)
    db.mark_listing_inactive(listing_id)
    assert db.get_listing_by_db_id(listing_id)["active"] == 0
