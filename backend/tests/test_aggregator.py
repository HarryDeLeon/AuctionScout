from app.research.aggregator import aggregate
from app.research.sources.base import ComparableRecord


def test_aggregate_returns_stats():
    comps = [
        ComparableRecord("ebay", "A", 100, "CAD", None, "u1", None, "active_ask", 0.9),
        ComparableRecord("ebay", "B", 120, "CAD", None, "u2", None, "active_ask", 0.8),
        ComparableRecord("ebay", "C", 80, "CAD", None, "u3", None, "active_ask", 0.7),
    ]
    result = aggregate(comps)
    assert result.low == 80
    assert result.high == 120
    assert result.median == 100
    assert result.sample_size == 3
    assert 0 < result.confidence <= 1
