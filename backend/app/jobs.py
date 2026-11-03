from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.registry import registry
from app.config import settings
from app.db import SessionLocal
from app.events import event_bus
from app.models import Comparable, Lot, ResearchRun, Search
from app.research.pipeline import ResearchPipeline

pipeline = ResearchPipeline()


def _keyword_match(text: str, keywords: str | None) -> bool:
    if not keywords:
        return True
    text_lower = text.lower()
    tokens = [k.strip().lower() for k in keywords.split(",") if k.strip()]
    return all(token in text_lower for token in tokens)


def _domain_name(url: str) -> str:
    return urlparse(url).netloc.replace("www.", "")


def _lot_matches_price_filters(lot, min_price: float | None, max_price: float | None) -> bool:
    prices = [p for p in [lot.current_bid, lot.opening_bid] if p is not None]
    if min_price is None and max_price is None:
        return True
    if not prices:
        return False
    for price in prices:
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        return True
    return False


def _lot_is_active(lot) -> bool:
    return bool(getattr(lot, "is_active", True))


def _lot_price_value(lot) -> float:
    value = lot.current_bid if lot.current_bid is not None else lot.opening_bid
    if value is None:
        return float("inf")
    return value


async def enqueue_search(search_id: int) -> None:
    import asyncio

    asyncio.create_task(run_search(search_id))


async def run_search(search_id: int) -> None:
    async with SessionLocal() as db:
        search = await db.get(Search, search_id)
        if not search:
            return
        search.status = "fetching"
        await db.commit()
        await event_bus.publish(search_id, {"type": "progress", "status": "fetching"})
        adapter = registry.resolve(search.url)
        search.site = adapter.name
        await db.commit()

        try:
            fetched = await adapter.fetch_lots(search.url, max_items=max(search.max_items * 3, 30))
            kept = []
            for lot in fetched:
                if not _lot_is_active(lot):
                    continue
                if not _lot_matches_price_filters(lot, search.min_price, search.max_price):
                    continue
                if not _keyword_match(f"{lot.title} {lot.description or ''}", search.keywords):
                    continue
                kept.append(lot)
            reverse = search.price_sort_order == "desc"
            kept = sorted(kept, key=_lot_price_value, reverse=reverse)[: search.max_items]

            search.status = "researching"
            search.progress_total = len(kept)
            search.progress_done = 0
            if adapter.name == "generic":
                search.warning = f"Using generic adapter for {_domain_name(search.url)}. Data confidence may be lower."
            await db.commit()
            await event_bus.publish(search_id, {"type": "progress", "status": "researching", "total": len(kept)})

            for lot_record in kept:
                lot = Lot(
                    search_id=search.id,
                    lot_number=lot_record.lot_number,
                    title=lot_record.title,
                    description=lot_record.description,
                    image_url=lot_record.image_url,
                    current_bid=lot_record.current_bid,
                    opening_bid=lot_record.opening_bid,
                    estimate_low=lot_record.estimate_low,
                    estimate_high=lot_record.estimate_high,
                    currency=lot_record.currency or settings.default_currency,
                    buyers_premium_pct=lot_record.buyers_premium_pct,
                    ends_at=lot_record.ends_at,
                    lot_url=lot_record.lot_url,
                    raw=lot_record.raw,
                    confidence=lot_record.confidence,
                )
                db.add(lot)
                await db.flush()

                query, comps, agg, warning = await pipeline.run(lot.title, lot.description, image_url=lot.image_url)
                run = ResearchRun(
                    lot_id=lot.id,
                    query_text=query,
                    query_source="auto",
                    status="done",
                    low=agg.low,
                    high=agg.high,
                    median=agg.median,
                    sample_size=agg.sample_size,
                    confidence=agg.confidence,
                    warning=warning,
                )
                db.add(run)
                await db.flush()

                for comp in comps:
                    db.add(
                        Comparable(
                            research_run_id=run.id,
                            source=comp.source,
                            title=comp.title,
                            price=comp.price,
                            currency=comp.currency,
                            condition=comp.condition,
                            url=comp.url,
                            image_url=comp.image_url,
                            listing_type=comp.listing_type,
                            similarity=comp.similarity,
                        )
                    )

                search.progress_done += 1
                await db.commit()
                await event_bus.publish(
                    search_id,
                    {"type": "lot_researched", "done": search.progress_done, "total": search.progress_total, "lot_id": lot.id},
                )

            search.status = "done"
            search.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await event_bus.publish(search_id, {"type": "done"})
        except Exception as exc:  # noqa: BLE001
            search.status = "failed"
            search.error = str(exc)
            search.finished_at = datetime.now(timezone.utc)
            await db.commit()
            await event_bus.publish(search_id, {"type": "error", "error": str(exc)})


async def rerun_lot_research(db: AsyncSession, lot_id: int, query: str | None, use_image: bool) -> ResearchRun:
    lot = await db.get(Lot, lot_id)
    if not lot:
        raise ValueError("Lot not found")
    query_text, comps, agg, warning = await pipeline.run(
        lot.title,
        lot.description,
        query=query,
        use_image=use_image,
        image_url=lot.image_url,
    )
    run = ResearchRun(
        lot_id=lot.id,
        query_text=query_text,
        query_source="user" if query else "auto",
        status="done",
        low=agg.low,
        high=agg.high,
        median=agg.median,
        sample_size=agg.sample_size,
        confidence=agg.confidence,
        warning=warning,
    )
    db.add(run)
    await db.flush()
    for comp in comps:
        db.add(
            Comparable(
                research_run_id=run.id,
                source=comp.source,
                title=comp.title,
                price=comp.price,
                currency=comp.currency,
                condition=comp.condition,
                url=comp.url,
                image_url=comp.image_url,
                listing_type=comp.listing_type,
                similarity=comp.similarity,
            )
        )
    await db.commit()
    await db.refresh(run)
    return run
