from __future__ import annotations

import re
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup

from app.adapters.base import LotRecord
from app.adapters.helpers import parse_price, resolve_link


class UrbanAuctionsAdapter:
    name = "urbanauctions"
    url_patterns = [re.compile(r"urbanauctions\.ca", re.IGNORECASE)]

    @staticmethod
    def _candidate_cards(soup: BeautifulSoup) -> Iterable:
        cards = soup.select(".galleryUnit")
        if cards:
            return cards
        return soup.select(".lot, .auction-lot, article, li")

    @staticmethod
    def _clean_title(title: str) -> str:
        cleaned = re.sub(r"^\s*Lot\s*\d+\s+\d+\s+Bid\(s\)\s*", "", title, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bCurrent\s+Bid\b.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bTime\s+Remaining\b.*$", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def _active_only_url(url: str) -> str:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query["StatusFilter"] = "active_only"
        query.setdefault("ViewStyle", "grid")
        new_query = urlencode(query)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))

    def parse_lots(self, html: str, source_url: str, max_items: int = 50) -> list[LotRecord]:
        soup = BeautifulSoup(html, "html.parser")
        lots: list[LotRecord] = []

        for card in self._candidate_cards(soup):
            if len(lots) >= max_items:
                break
            title = ""
            title_text_el = card.select_one("h2.galleryTitle a, .galleryTitle a, h2, h3, .title")
            if title_text_el:
                title = title_text_el.get_text(" ", strip=True).strip()
            if len(title) < 4:
                title_img_el = card.select_one(".galleryImage img, img[alt]")
                if title_img_el and title_img_el.get("alt"):
                    title = title_img_el.get("alt").strip()
            title = self._clean_title(title)
            if len(title) < 4:
                continue
            lot_number_el = card.select_one(".lot-number, .number, .galleryTitle .small")
            desc_el = card.select_one(".description, p")
            price_el = card.select_one(".awe-rt-CurrentPrice .NumberPart, .galleryPrice .NumberPart, .bid, .current-bid, .price")
            opening_bid_el = card.select_one(".awe-rt-MinimumBid .NumberPart")
            end_time_el = card.select_one("[data-action-time]")
            image_el = card.select_one("img")
            link_el = card.select_one("h2.galleryTitle a[href], .galleryImage a[href], a[href]")
            lot_number_text = lot_number_el.get_text(" ", strip=True) if lot_number_el else None
            lot_number = None
            if lot_number_text:
                match = re.search(r"Lot\s*([0-9]+)", lot_number_text, flags=re.IGNORECASE)
                lot_number = match.group(1) if match else lot_number_text
            description = desc_el.get_text(" ", strip=True) if desc_el else None
            if description and "current bid" in description.lower() and "time remaining" in description.lower():
                description = None
            ends_at = end_time_el.get("data-action-time") if end_time_el else None
            lots.append(
                LotRecord(
                    lot_number=lot_number,
                    title=title,
                    description=description,
                    image_url=image_el.get("src") if image_el else None,
                    current_bid=parse_price(price_el.get_text(" ", strip=True) if price_el else None),
                    opening_bid=parse_price(opening_bid_el.get_text(" ", strip=True) if opening_bid_el else None),
                    estimate_low=None,
                    estimate_high=None,
                    currency="CAD",
                    buyers_premium_pct=None,
                    ends_at=ends_at,
                    lot_url=resolve_link(source_url, link_el.get("href") if link_el else None),
                    is_active=True,
                    raw={"source": "html"},
                    confidence=0.6,
                )
            )
        return lots

    async def fetch_lots(self, url: str, max_items: int = 50) -> list[LotRecord]:
        headers = {"User-Agent": "Mozilla/5.0 AuctionScout/1.0"}
        target_url = self._active_only_url(url)
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(target_url)
            response.raise_for_status()
        return self.parse_lots(response.text, source_url=target_url, max_items=max_items)
