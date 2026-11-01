from __future__ import annotations

import re
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from app.research.sources.base import ComparableRecord


class DuckDuckGoPriceSource:
    base_urls = [
        "https://html.duckduckgo.com/html/",
        "https://duckduckgo.com/html/",
    ]

    @staticmethod
    def _similarity(query: str, title: str) -> float:
        query_tokens = {t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 2}
        title_tokens = {t for t in re.findall(r"[a-zA-Z0-9]+", title.lower()) if len(t) > 2}
        if not query_tokens:
            return 0.4
        overlap = len(query_tokens & title_tokens) / len(query_tokens)
        return max(0.25, min(0.85, round(overlap, 3)))

    @staticmethod
    def _query_tokens(query: str) -> set[str]:
        stop = {"new", "with", "for", "the", "and", "price"}
        return {t for t in re.findall(r"[a-zA-Z0-9]+", query.lower()) if len(t) > 2 and t not in stop}

    @staticmethod
    def _is_category_or_search_url(url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        query = parsed.query.lower()
        bad_path_markers = ["/kp/", "/search", "/s/", "/s?", "/collections/", "/category", "/categories"]
        if any(marker in path for marker in bad_path_markers):
            return True
        bad_query_markers = ["k=", "q=", "search=", "query="]
        return any(marker in query for marker in bad_query_markers)

    @staticmethod
    def _title_is_generic(title: str) -> bool:
        t = title.lower()
        generic_markers = ["shop", "results", "category", "deals", "products", "search"]
        return any(marker in t for marker in generic_markers) and "milwaukee" in t

    @staticmethod
    def _has_strong_query_match(query: str, title: str, url: str) -> bool:
        tokens = DuckDuckGoPriceSource._query_tokens(query)
        haystack = f"{title} {url}".lower()
        matches = sum(1 for token in tokens if token in haystack)
        return matches >= 2

    @staticmethod
    def _currency_from_text(text: str) -> str:
        upper = text.upper()
        if "USD" in upper or "US$" in upper or "US $" in upper:
            return "USD"
        if "CAD" in upper or "C$" in upper or "C $" in upper:
            return "CAD"
        return "CAD"

    def parse_html(self, html: str, query: str, max_items: int = 12) -> list[ComparableRecord]:
        soup = BeautifulSoup(html, "html.parser")
        results: list[ComparableRecord] = []
        rows = soup.select(".result")
        for row in rows:
            if len(results) >= max_items:
                break
            link_el = row.select_one(".result__a[href], a[href]")
            title_el = row.select_one(".result__a")
            snippet_el = row.select_one(".result__snippet")
            if not link_el:
                continue
            title = title_el.get_text(" ", strip=True) if title_el else link_el.get_text(" ", strip=True)
            snippet = snippet_el.get_text(" ", strip=True) if snippet_el else ""
            price_text = f"{title} {snippet}"
            price = self._extract_price(price_text)
            url = link_el.get("href", "")
            if url.startswith("//"):
                url = f"https:{url}"
            url = self._unwrap_duckduckgo_redirect(url)
            if self._is_category_or_search_url(url):
                continue
            if self._title_is_generic(title):
                continue
            if not self._has_strong_query_match(query, title, url):
                continue
            if price is None:
                continue
            results.append(
                ComparableRecord(
                    source="duckduckgo_price",
                    title=title or "Web result",
                    price=price,
                    currency=self._currency_from_text(price_text),
                    condition=None,
                    url=url,
                    image_url=None,
                    listing_type="retail",
                    similarity=self._similarity(query=query, title=title or ""),
                )
            )
        return results

    @staticmethod
    def _unwrap_duckduckgo_redirect(url: str) -> str:
        parsed = urlparse(url)
        if "duckduckgo.com" not in parsed.netloc or not parsed.path.startswith("/l/"):
            return url
        query = parse_qs(parsed.query)
        uddg = query.get("uddg", [])
        if not uddg:
            return url
        return unquote(uddg[0])

    @staticmethod
    def _extract_price_from_page(html: str) -> tuple[float | None, str]:
        text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
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
                if value <= 1:
                    continue
                return value, currency
            except ValueError:
                continue
        return None, "CAD"

    async def search(self, query: str, use_image: bool = False) -> list[ComparableRecord]:
        del use_image
        q = f"{query} price"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-CA,en;q=0.9",
            "Referer": "https://duckduckgo.com/",
        }
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, headers=headers) as client:
            html_text = ""
            for base_url in self.base_urls:
                response = await client.get(f"{base_url}?q={quote_plus(q)}")
                response.raise_for_status()
                html_text = response.text
                if BeautifulSoup(html_text, "html.parser").select(".result"):
                    break

            parsed = self.parse_html(html_text, query=q, max_items=12)
            if parsed:
                return parsed

            soup = BeautifulSoup(html_text, "html.parser")
            candidates: list[tuple[str, str]] = []
            for row in soup.select(".result"):
                a = row.select_one(".result__a[href], a[href]")
                if not a:
                    continue
                title = a.get_text(" ", strip=True) or "Web result"
                href = a.get("href", "")
                if href.startswith("//"):
                    href = f"https:{href}"
                href = self._unwrap_duckduckgo_redirect(href)
                if not href.startswith("http"):
                    continue
                if self._is_category_or_search_url(href):
                    continue
                if self._title_is_generic(title):
                    continue
                if not self._has_strong_query_match(q, title, href):
                    continue
                candidates.append((title, href))
                if len(candidates) >= 8:
                    break

            fallback_results: list[ComparableRecord] = []
            for title, href in candidates:
                try:
                    page_response = await client.get(href, timeout=10.0, follow_redirects=True)
                    page_response.raise_for_status()
                except Exception:  # noqa: BLE001
                    continue
                price, currency = self._extract_price_from_page(page_response.text)
                if price is None:
                    continue
                if price > 2500:
                    continue
                fallback_results.append(
                    ComparableRecord(
                        source="duckduckgo_price",
                        title=title,
                        price=price,
                        currency=currency,
                        condition=None,
                        url=href,
                        image_url=None,
                        listing_type="retail",
                        similarity=self._similarity(query=q, title=title),
                    )
                )
                if len(fallback_results) >= 12:
                    break
            return fallback_results

    @staticmethod
    def _extract_price(text: str) -> float | None:
        patterns = [
            r"(?:C\$|C \$|CAD)\s*(\d+(?:\.\d{1,2})?)",
            r"(?:US\$|US \$|USD)\s*(\d+(?:\.\d{1,2})?)",
            r"\$\s*(\d+(?:\.\d{1,2})?)",
            r"\b(\d+\.\d{2})\b",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            try:
                value = float(match.group(1))
                if value <= 1:
                    continue
                return value
            except ValueError:
                continue
        return None
