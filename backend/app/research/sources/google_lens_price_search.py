from __future__ import annotations

import re
from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.research.sources.base import ComparableRecord


class GoogleLensPriceSource:
    """Best-effort reverse image lookup using the Google Lens web endpoint.

    Google does not provide a stable public API for Lens in this project, so this
    parser intentionally remains defensive and returns an empty list when no
    parseable listing+price pairs are found.
    """

    endpoint = "https://lens.google.com/uploadbyurl"

    @staticmethod
    def _extract_price(text: str) -> tuple[float | None, str]:
        patterns = [
            (r"(?:C\$|C \$|CAD)\s*(\d+(?:\.\d{1,2})?)", "CAD"),
            (r"(?:US\$|US \$|USD)\s*(\d+(?:\.\d{1,2})?)", "USD"),
            (r"\$\s*(\d+(?:\.\d{1,2})?)", "CAD"),
        ]
        for pattern, currency in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                value = float(match.group(1))
            except ValueError:
                continue
            if value <= 1:
                continue
            return value, currency
        return None, "CAD"

    @staticmethod
    def _similarity(query: str, title: str) -> float:
        query_tokens = {t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 2}
        title_tokens = {t for t in re.findall(r"[a-zA-Z0-9]+", title.lower()) if len(t) > 2}
        if not query_tokens:
            return 0.5
        overlap = len(query_tokens & title_tokens) / len(query_tokens)
        return max(0.3, min(0.9, round(overlap + 0.1, 3)))

    @staticmethod
    def _extract_target_url(href: str) -> str | None:
        if not href:
            return None
        if href.startswith("//"):
            href = f"https:{href}"
        if href.startswith("/"):
            return None
        if href.startswith("http"):
            parsed = urlparse(href)
            if "google." in parsed.netloc or parsed.netloc.endswith("gstatic.com"):
                return None
            return href

        if "imgurl=" in href:
            parts = href.split("imgurl=", 1)
            if len(parts) == 2:
                return unquote(parts[1].split("&", 1)[0])

        return None

    def parse_html(self, html: str, query: str, max_items: int = 8) -> list[ComparableRecord]:
        soup = BeautifulSoup(html, "html.parser")
        result: list[ComparableRecord] = []
        seen_urls: set[str] = set()

        for link in soup.select("a[href]"):
            href = link.get("href", "")
            target_url = self._extract_target_url(href)
            if not target_url or target_url in seen_urls:
                continue

            # Lens often nests metadata in nearby containers; include parent text.
            title = link.get_text(" ", strip=True)
            parent_text = link.parent.get_text(" ", strip=True) if link.parent else ""
            text = " ".join(part for part in [title, parent_text] if part).strip()
            if not text:
                continue

            price, currency = self._extract_price(text)
            if price is None:
                continue

            if price > 25000:
                continue

            result.append(
                ComparableRecord(
                    source="google_lens",
                    title=title or "Image result",
                    price=price,
                    currency=currency,
                    condition=None,
                    url=target_url,
                    image_url=None,
                    listing_type="visual_match",
                    similarity=self._similarity(query, title or text),
                )
            )
            seen_urls.add(target_url)
            if len(result) >= max_items:
                break

        return result

    async def search(
        self,
        query: str,
        use_image: bool = False,
        image_url: str | None = None,
    ) -> list[ComparableRecord]:
        if not use_image or not image_url:
            return []

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-CA,en;q=0.9",
            "Referer": "https://www.google.com/",
        }
        params = {
            "url": image_url,
            "hl": "en",
        }

        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            response = await client.get(self.endpoint, params=params)
            response.raise_for_status()
            return self.parse_html(response.text, query=query, max_items=8)
