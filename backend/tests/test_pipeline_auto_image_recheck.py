import asyncio

from app.research.pipeline import ResearchPipeline
from app.research.sources.base import ComparableRecord


class _StubSource:
    def __init__(self, items: list[ComparableRecord]):
        self.items = items
        self.calls = 0

    async def search(self, query: str, use_image: bool = False, image_url: str | None = None) -> list[ComparableRecord]:
        self.calls += 1
        return self.items


def _comp(title: str, price: float, similarity: float, source: str = "stub") -> ComparableRecord:
    return ComparableRecord(
        source=source,
        title=title,
        price=price,
        currency="CAD",
        condition=None,
        url=f"https://example.com/{title}",
        image_url=None,
        listing_type="active_ask",
        similarity=similarity,
    )


def test_auto_image_recheck_runs_when_text_confidence_is_low(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "enable_auto_image_recheck", True)
    monkeypatch.setattr(settings, "auto_image_recheck_confidence_threshold", 0.45)

    pipeline = ResearchPipeline()
    low_conf_text = _StubSource([_comp("text-only", 100.0, 0.3, source="text")])
    image_stub = _StubSource([_comp("image-hit", 120.0, 0.8, source="google_lens")])
    pipeline.text_sources = [low_conf_text]
    pipeline.image_sources = [image_stub]

    _, comps, agg, warning = asyncio.run(
        pipeline.run(
            title="Milwaukee Battery",
            description="",
            image_url="https://images.example.com/item.jpg",
        )
    )

    assert low_conf_text.calls == 1
    assert image_stub.calls == 1
    assert len(comps) == 2
    assert agg.sample_size == 2
    assert warning is not None
    assert "Auto image recheck applied" in warning


def test_auto_image_recheck_skips_when_text_confidence_is_high(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "enable_auto_image_recheck", True)
    monkeypatch.setattr(settings, "auto_image_recheck_confidence_threshold", 0.45)

    pipeline = ResearchPipeline()
    high_conf_items = [_comp(f"text-strong-{idx}", 100.0 + idx, 0.9, source="text") for idx in range(10)]
    high_conf_text = _StubSource(high_conf_items)
    image_stub = _StubSource([_comp("image-hit", 120.0, 0.8, source="google_lens")])
    pipeline.text_sources = [high_conf_text]
    pipeline.image_sources = [image_stub]

    _, comps, agg, warning = asyncio.run(
        pipeline.run(
            title="Milwaukee Battery",
            description="",
            image_url="https://images.example.com/item.jpg",
        )
    )

    assert high_conf_text.calls == 1
    assert image_stub.calls == 0
    assert len(comps) == 10
    assert agg.sample_size == 10
    assert warning is None
