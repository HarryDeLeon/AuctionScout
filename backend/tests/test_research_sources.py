from pathlib import Path

from app.research.sources.ebay_web_fallback import EbayWebFallbackSource


def test_ebay_web_fallback_parser_extracts_comparables():
    html = (Path(__file__).parent / "fixtures" / "html" / "ebay_web_fallback_sample.html").read_text(encoding="utf-8")
    source = EbayWebFallbackSource()
    comparables = source.parse_html(html, query="Milwaukee battery", max_items=10)

    assert len(comparables) == 2
    assert comparables[0].source == "ebay_web_fallback"
    assert comparables[0].title == "Milwaukee M12 Red Lithium Battery CP1.5"
    assert comparables[0].price == 39.99
    assert comparables[0].currency == "CAD"
    assert comparables[1].currency == "USD"
