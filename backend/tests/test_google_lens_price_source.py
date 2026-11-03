from app.research.sources.google_lens_price_search import GoogleLensPriceSource


def test_google_lens_parser_extracts_price_candidates():
    html = """
    <html>
      <body>
        <div>
          <a href="https://example.com/item-1">Milwaukee M18 Battery Pack</a>
          <span>CAD 129.99</span>
        </div>
        <div>
          <a href="https://example.com/item-2">Milwaukee Drill Combo</a>
          <span>US $89.00</span>
        </div>
        <div>
          <a href="https://www.google.com/some-internal-link">Ignore internal</a>
          <span>$99.99</span>
        </div>
      </body>
    </html>
    """

    source = GoogleLensPriceSource()
    comparables = source.parse_html(html, query="Milwaukee battery", max_items=10)

    assert len(comparables) == 2
    assert comparables[0].source == "google_lens"
    assert comparables[0].price == 129.99
    assert comparables[0].currency == "CAD"
    assert comparables[1].price == 89.0
    assert comparables[1].currency == "USD"
