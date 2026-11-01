from types import SimpleNamespace

from app.jobs import _lot_matches_price_filters


def _lot(current_bid, opening_bid):
    return SimpleNamespace(current_bid=current_bid, opening_bid=opening_bid)


def test_matches_if_either_bid_or_quick_bid_is_in_range():
    lot = _lot(current_bid=150.0, opening_bid=100.0)
    assert _lot_matches_price_filters(lot, min_price=None, max_price=125.0)


def test_matches_if_current_bid_is_in_range():
    lot = _lot(current_bid=120.0, opening_bid=200.0)
    assert _lot_matches_price_filters(lot, min_price=110.0, max_price=130.0)


def test_no_match_when_neither_bid_nor_quick_bid_meets_range():
    lot = _lot(current_bid=150.0, opening_bid=140.0)
    assert not _lot_matches_price_filters(lot, min_price=None, max_price=125.0)
