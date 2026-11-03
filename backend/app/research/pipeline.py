from __future__ import annotations

from app.config import settings
from app.research.aggregator import AggregateResult, aggregate
from app.research.query_builder import build_query
from app.research.sources.base import ComparableRecord, SourceConfigurationError
from app.research.sources.duckduckgo_price_search import DuckDuckGoPriceSource
from app.research.sources.ebay_browse import EbayBrowseSource
from app.research.sources.ebay_web_fallback import EbayWebFallbackSource
from app.research.sources.google_lens_price_search import GoogleLensPriceSource


class ResearchPipeline:
    def __init__(self) -> None:
        self.text_sources = [
            EbayBrowseSource(),
            EbayWebFallbackSource(),
            DuckDuckGoPriceSource(),
        ]
        self.image_sources = [
            GoogleLensPriceSource(),
        ]

    async def run(
        self,
        title: str,
        description: str | None,
        query: str | None = None,
        use_image: bool = False,
        image_url: str | None = None,
    ):
        research_query, is_bulk = (
            (query.strip(), False)
            if query and query.strip()
            else build_query(title=title, description=description, llm_enabled=settings.enable_llm_query_builder)
        )
        comparables: list[ComparableRecord] = []
        warnings: list[str] = []
        for source in self.text_sources:
            try:
                items = await source.search(research_query, use_image=use_image, image_url=image_url)
                comparables.extend(items)
            except SourceConfigurationError as exc:
                warnings.append(str(exc))
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"{source.__class__.__name__} failed: {exc}")

        text_aggregate: AggregateResult = aggregate(comparables)

        should_auto_recheck = (
            settings.enable_auto_image_recheck
            and bool(image_url)
            and text_aggregate.confidence < settings.auto_image_recheck_confidence_threshold
        )
        should_use_image = bool(image_url) and (use_image or should_auto_recheck)

        if use_image and not image_url:
            warnings.append("Image recheck requested, but this lot has no image URL.")

        if should_use_image:
            image_items_before = len(comparables)
            for source in self.image_sources:
                try:
                    items = await source.search(research_query, use_image=True, image_url=image_url)
                    comparables.extend(items)
                except SourceConfigurationError as exc:
                    warnings.append(str(exc))
                except Exception as exc:  # noqa: BLE001
                    warnings.append(f"{source.__class__.__name__} failed: {exc}")

            if should_auto_recheck and len(comparables) > image_items_before:
                warnings.append("Auto image recheck applied due to low text-search confidence.")

        aggregate_result: AggregateResult = aggregate(comparables)
        if is_bulk:
            warnings.append("Bulk-lot detected; pricing confidence is reduced.")
            aggregate_result.confidence = min(aggregate_result.confidence, 0.35)
        return research_query, comparables, aggregate_result, "; ".join(warnings) if warnings else None
