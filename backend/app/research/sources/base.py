from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ComparableRecord:
    source: str
    title: str
    price: float
    currency: str
    condition: str | None
    url: str
    image_url: str | None
    listing_type: str
    similarity: float


class SourceConfigurationError(RuntimeError):
    pass


class PriceSource(Protocol):
    async def search(
        self,
        query: str,
        use_image: bool = False,
        image_url: str | None = None,
    ) -> list[ComparableRecord]:
        ...
