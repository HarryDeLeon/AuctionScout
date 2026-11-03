from pathlib import Path

from app.adapters.generic import GenericAdapter
from app.adapters.liveauctioneers import LiveAuctioneersAdapter
from app.adapters.urbanauctions import UrbanAuctionsAdapter

FIXTURES = Path(__file__).parent / "fixtures" / "html"


def _read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_liveauctioneers_fixture_parse():
    adapter = LiveAuctioneersAdapter()
    lots = adapter.parse_lots(
        _read_fixture("liveauctioneers_sample.html"),
        source_url="https://www.liveauctioneers.com/catalog/sample",
        max_items=10,
    )
    assert len(lots) == 2
    assert lots[0].lot_number == "Lot 101"
    assert lots[0].title == "Makita Cordless Drill Set XFD12"
    assert lots[0].current_bid == 125.00
    assert lots[0].lot_url == "https://www.liveauctioneers.com/item/101"


def test_liveauctioneers_block_page_detection():
    adapter = LiveAuctioneersAdapter()
    blocked_html = "<html><body>Request unsuccessful. Incapsula incident ID: 12345</body></html>"
    assert adapter._looks_like_block_page(blocked_html)


def test_liveauctioneers_non_block_page_detection():
    adapter = LiveAuctioneersAdapter()
    normal_html = _read_fixture("liveauctioneers_sample.html")
    assert not adapter._looks_like_block_page(normal_html)


def test_urbanauctions_fixture_parse():
    adapter = UrbanAuctionsAdapter()
    lots = adapter.parse_lots(
        _read_fixture("urbanauctions_sample.html"),
        source_url="https://urbanauctions.ca/current-auction",
        max_items=10,
    )
    assert len(lots) == 2
    assert lots[0].lot_number == "12"
    assert lots[0].description == "Includes base and edge guide."
    assert lots[0].current_bid == 140.00
    assert lots[0].lot_url == "https://urbanauctions.ca/auctions/lot/12"


def test_urbanauctions_gallery_fixture_parse():
    adapter = UrbanAuctionsAdapter()
    lots = adapter.parse_lots(
        _read_fixture("urbanauctions_gallery_sample.html"),
        source_url="https://urbanauctions.ca/Event/Details/172162755/GENERAL-AUCTION/C165507/Tools-",
        max_items=10,
    )
    assert len(lots) == 1
    assert lots[0].lot_number == "156"
    assert lots[0].title == "NEW MILWAUKEE M12 RED LITHIUM CP1.5 BATTERY"
    assert lots[0].current_bid == 20.00
    assert lots[0].opening_bid == 25.00
    assert lots[0].lot_url == "https://urbanauctions.ca/Event/LotDetails/172201544/NEW-MILWAUKEE-M12-RED-LITHIUM-CP15-BATTERY"
    assert lots[0].is_active


def test_generic_fixture_parse():
    adapter = GenericAdapter()
    lots = adapter.parse_lots(
        _read_fixture("generic_sample.html"),
        source_url="https://example-auctions.test/catalog",
        max_items=10,
    )
    assert len(lots) == 2
    assert lots[0].title == "Ryobi 18V Circular Saw P507"
    assert lots[0].current_bid == 55.00
    assert lots[0].lot_url == "https://example-auctions.test/lot/1"
