from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class LotRecord:
    lot_number: str | None
    title: str
    description: str | None
    image_url: str | None
    current_bid: float | None
    opening_bid: float | None
    estimate_low: float | None
    estimate_high: float | None
    currency: str
    buyers_premium_pct: float | None
    ends_at: str | None
    lot_url: str | None
    is_active: bool = True
    raw: dict = field(default_factory=dict)
    confidence: float = 0.7


class AuctionAdapter(Protocol):
    name: str
    url_patterns: list[re.Pattern[str]]

    async def fetch_lots(self, url: str, max_items: int = 50) -> list[LotRecord]:
        ...
