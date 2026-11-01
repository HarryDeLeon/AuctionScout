from pathlib import Path

from app.research.sources.duckduckgo_price_search import DuckDuckGoPriceSource


def test_duckduckgo_price_parse_extracts_price_links():
    html = (Path(__file__).parent / "fixtures" / "html" / "duckduckgo_price_sample.html").read_text(encoding="utf-8")
    source = DuckDuckGoPriceSource()
    results = source.parse_html(html, query="milwaukee m12 battery", max_items=10)

    assert len(results) == 1
    assert results[0].source == "duckduckgo_price"
    assert results[0].price == 49.99
    assert results[0].currency == "CAD"
    assert results[0].url == "https://example.com/milwaukee-battery"
