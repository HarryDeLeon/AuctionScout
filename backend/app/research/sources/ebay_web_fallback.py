from __future__ import annotations

from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from app.adapters.helpers import parse_price
from app.research.sources.base import ComparableRecord


class EbayWebFallbackSource:
    base_url = "https://www.ebay.ca/sch/i.html"

    @staticmethod
    def _similarity(query: str, title: str) -> float:
        query_tokens = {t for t in query.lower().split() if len(t) > 2}
        title_tokens = {t for t in title.lower().split() if len(t) > 2}
        if not query_tokens:
            return 0.4
        overlap = len(query_tokens & title_tokens)
        ratio = overlap / len(query_tokens)
        return max(0.3, min(0.9, round(ratio, 3)))

    @staticmethod
    def _currency_from_price_text(price_text: str) -> str:
        normalized = price_text.upper()
        if "US $" in normalized or "USD" in normalized:
            return "USD"
        if "C $" in normalized or "CAD" in normalized:
            return "CAD"
        return "CAD"

    def parse_html(self, html: str, query: str, max_items: int = 12) -> list[ComparableRecord]:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select(".s-item")
        comparables: list[ComparableRecord] = []
        for row in rows:
            if len(comparables) >= max_items:
                break
            title_el = row.select_one(".s-item__title")
            price_el = row.select_one(".s-item__price")
            link_el = row.select_one("a.s-item__link[href]")
            image_el = row.select_one(".s-item__image-img")
            if not title_el or not price_el or not link_el:
                continue
            title = title_el.get_text(" ", strip=True)
            if not title or "shop on ebay" in title.lower():
                continue
            price_text = price_el.get_text(" ", strip=True)
            price = parse_price(price_text)
            if price is None:
                continue
            comparables.append(
                ComparableRecord(
                    source="ebay_web_fallback",
                    title=title,
                    price=price,
                    currency=self._currency_from_price_text(price_text),
                    condition=None,
                    url=link_el.get("href", ""),
                    image_url=image_el.get("src") if image_el else None,
                    listing_type="active_ask",
                    similarity=self._similarity(query=query, title=title),
                )
            )
        return comparables

    async def search(self, query: str, use_image: bool = False) -> list[ComparableRecord]:
        del use_image
        params = {
            "_nkw": query,
            "_sacat": "0",
            "LH_BIN": "1",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 AuctionScout/1.0",
            "Accept-Language": "en-CA,en;q=0.9",
        }
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(
                f"{self.base_url}?_nkw={quote_plus(params['_nkw'])}&_sacat={params['_sacat']}&LH_BIN={params['LH_BIN']}"
            )
            response.raise_for_status()
        return self.parse_html(response.text, query=query, max_items=12)
