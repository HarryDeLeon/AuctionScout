from __future__ import annotations

from app.config import settings
from app.research.aggregator import AggregateResult, aggregate
from app.research.query_builder import build_query
from app.research.sources.base import ComparableRecord, SourceConfigurationError
from app.research.sources.duckduckgo_price_search import DuckDuckGoPriceSource
from app.research.sources.ebay_browse import EbayBrowseSource
from app.research.sources.ebay_web_fallback import EbayWebFallbackSource


class ResearchPipeline:
    def __init__(self) -> None:
        self.sources = [EbayBrowseSource(), EbayWebFallbackSource(), DuckDuckGoPriceSource()]

    async def run(self, title: str, description: str | None, query: str | None = None, use_image: bool = False):
        research_query, is_bulk = (
            (query.strip(), False)
            if query and query.strip()
            else build_query(title=title, description=description, llm_enabled=settings.enable_llm_query_builder)
        )
        comparables: list[ComparableRecord] = []
        warnings: list[str] = []
        for source in self.sources:
            try:
                items = await source.search(research_query, use_image=use_image)
                comparables.extend(items)
            except SourceConfigurationError as exc:
                warnings.append(str(exc))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{source.__class__.__name__} failed: {exc}")

        aggregate_result: AggregateResult = aggregate(comparables)
        if is_bulk:
            warnings.append("Bulk-lot detected; pricing confidence is reduced.")
            aggregate_result.confidence = min(aggregate_result.confidence, 0.35)
        return research_query, comparables, aggregate_result, "; ".join(warnings) if warnings else None
