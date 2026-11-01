from app.services.pricing import all_in_cost, margin_indicator


def test_all_in_cost():
    assert all_in_cost(bid=100, buyers_premium_pct=0.1, tax_rate=0.12, shipping_estimate=40) == 163.2


def test_margin_indicator():
    assert margin_indicator(100, 140, 130, 0.3) == "green"
    assert margin_indicator(100, 120, 130, 0.3) == "amber"
    assert margin_indicator(100, 110, 115, 0.3) == "red"
    assert margin_indicator(None, 110, 120, 0.3) == "grey"
