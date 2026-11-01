from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from app.research.sources.base import ComparableRecord


@dataclass
class AggregateResult:
    low: float | None
    high: float | None
    median: float | None
    sample_size: int
    confidence: float


def aggregate(comparables: list[ComparableRecord], min_similarity: float = 0.25) -> AggregateResult:
    filtered = [c for c in comparables if c.similarity >= min_similarity and c.price > 0]
    if not filtered:
        return AggregateResult(low=None, high=None, median=None, sample_size=0, confidence=0.0)
    prices = sorted(c.price for c in filtered)
    low = prices[0]
    high = prices[-1]
    med = float(median(prices))
    avg_similarity = sum(c.similarity for c in filtered) / len(filtered)
    confidence = min(1.0, (len(filtered) / 10.0) * avg_similarity)
    return AggregateResult(low=low, high=high, median=med, sample_size=len(filtered), confidence=round(confidence, 3))
