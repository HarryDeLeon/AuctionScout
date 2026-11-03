from app.imports.csv_lots import parse_lots_csv


def test_parse_lots_csv_extracts_rows_and_prices():
    csv_text = """lot_number,title,current_bid,opening_bid,image_url,lot_url,currency
101,Gold Ring,450.00,400.00,https://img.example/101.jpg,https://auction.example/101,CAD
102,Diamond Pendant,999.99,800.00,https://img.example/102.jpg,https://auction.example/102,USD
"""

    parsed = parse_lots_csv(csv_text, max_items=10)

    assert len(parsed.lots) == 2
    assert parsed.warnings == []
    assert parsed.lots[0].lot_number == "101"
    assert parsed.lots[0].title == "Gold Ring"
    assert parsed.lots[0].current_bid == 450.0
    assert parsed.lots[1].currency == "USD"


def test_parse_lots_csv_skips_rows_without_title():
    csv_text = """lot_number,title,current_bid
101,,450.00
102,Diamond Pendant,999.99
"""

    parsed = parse_lots_csv(csv_text, max_items=10)

    assert len(parsed.lots) == 1
    assert parsed.lots[0].title == "Diamond Pendant"
    assert parsed.warnings
    assert "missing title" in parsed.warnings[0].lower()
