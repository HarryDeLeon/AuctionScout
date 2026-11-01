from __future__ import annotations

import re
from urllib.parse import urljoin


def parse_price(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d{1,2})?)", text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def resolve_link(base_url: str, href: str | None) -> str | None:
    if not href:
        return None
    return urljoin(base_url, href)
