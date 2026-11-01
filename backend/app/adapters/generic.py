from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from app.adapters.base import LotRecord
from app.adapters.helpers import parse_price, resolve_link


class GenericAdapter:
    name = "generic"
    url_patterns = [re.compile(r".*", re.IGNORECASE)]

    def parse_lots(self, html: str, source_url: str, max_items: int = 50) -> list[LotRecord]:
        soup = BeautifulSoup(html, "html.parser")
        lots: list[LotRecord] = []
        cards = soup.select("article, .card, li, tr")
        for card in cards:
            if len(lots) >= max_items:
                break
            title_el = card.select_one("h1, h2, h3, .title, a")
            if not title_el:
                continue
            title = title_el.get_text(" ", strip=True)
            if len(title) < 8:
                continue
            price_el = card.select_one(".price, .bid, [class*='price']")
            link_el = card.select_one("a[href]")
            img_el = card.select_one("img")
            lots.append(
                LotRecord(
                    lot_number=None,
                    title=title,
                    description=None,
                    image_url=img_el.get("src") if img_el else None,
                    current_bid=parse_price(price_el.get_text(" ", strip=True) if price_el else None),
                    opening_bid=None,
                    estimate_low=None,
                    estimate_high=None,
                    currency="CAD",
                    buyers_premium_pct=None,
                    ends_at=None,
                    lot_url=resolve_link(source_url, link_el.get("href") if link_el else None),
                    raw={"source": "generic"},
                    confidence=0.4,
                )
            )
        return lots

    async def fetch_lots(self, url: str, max_items: int = 50) -> list[LotRecord]:
        headers = {"User-Agent": "Mozilla/5.0 AuctionScout/1.0"}
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(url)
            response.raise_for_status()
        return self.parse_lots(response.text, source_url=url, max_items=max_items)
