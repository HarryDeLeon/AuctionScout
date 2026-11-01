from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Comparable, Lot, ResearchRun, Search
from app.schemas import ComparableOut, LotDetail, LotOut, ResearchRunOut, SearchDetail, SearchSummary


async def build_research_out(db: AsyncSession, run: ResearchRun) -> ResearchRunOut:
    comps = (
        (await db.execute(select(Comparable).where(Comparable.research_run_id == run.id).order_by(Comparable.similarity.desc())))
        .scalars()
        .all()
    )
    return ResearchRunOut(
        id=run.id,
        query_text=run.query_text,
        query_source=run.query_source,
        status=run.status,
        low=run.low,
        high=run.high,
        median=run.median,
        sample_size=run.sample_size,
        confidence=run.confidence,
        warning=run.warning,
        comparables=[
            ComparableOut(
                id=c.id,
                source=c.source,
                title=c.title,
                price=c.price,
                currency=c.currency,
                condition=c.condition,
                url=c.url,
                image_url=c.image_url,
                listing_type=c.listing_type,
                similarity=c.similarity,
            )
            for c in comps
        ],
    )


async def build_lot_out(db: AsyncSession, lot: Lot) -> LotOut:
    latest = (
        (
            await db.execute(
                select(ResearchRun).where(ResearchRun.lot_id == lot.id).order_by(ResearchRun.created_at.desc()).limit(1)
            )
        )
        .scalars()
        .first()
    )
    latest_out = await build_research_out(db, latest) if latest else None
    return LotOut(
        id=lot.id,
        lot_number=lot.lot_number,
        title=lot.title,
        description=lot.description,
        image_url=lot.image_url,
        current_bid=lot.current_bid,
        opening_bid=lot.opening_bid,
        estimate_low=lot.estimate_low,
        estimate_high=lot.estimate_high,
        currency=lot.currency,
        buyers_premium_pct=lot.buyers_premium_pct,
        ends_at=lot.ends_at,
        lot_url=lot.lot_url,
        confidence=lot.confidence,
        latest_research=latest_out,
    )


async def build_search_summary(search: Search) -> SearchSummary:
    return SearchSummary(
        id=search.id,
        name=search.name,
        url=search.url,
        site=search.site,
        status=search.status,
        progress_done=search.progress_done,
        progress_total=search.progress_total,
        price_sort_order=search.price_sort_order,
        warning=search.warning,
        error=search.error,
        created_at=search.created_at.isoformat(),
        finished_at=search.finished_at.isoformat() if search.finished_at else None,
    )


async def build_search_detail(db: AsyncSession, search: Search) -> SearchDetail:
    lots = (
        (await db.execute(select(Lot).where(Lot.search_id == search.id).order_by(Lot.id.asc())))
        .scalars()
        .all()
    )
    lot_out = [await build_lot_out(db, lot) for lot in lots]
    summary = await build_search_summary(search)
    return SearchDetail(
        **summary.model_dump(),
        min_price=search.min_price,
        max_price=search.max_price,
        max_items=search.max_items,
        keywords=search.keywords,
        lots=lot_out,
    )


async def build_lot_detail(db: AsyncSession, lot: Lot) -> LotDetail:
    lot_out = await build_lot_out(db, lot)
    runs = (
        (await db.execute(select(ResearchRun).where(ResearchRun.lot_id == lot.id).order_by(ResearchRun.created_at.desc())))
        .scalars()
        .all()
    )
    run_out = [await build_research_out(db, run) for run in runs]
    return LotDetail(**lot_out.model_dump(), research_runs=run_out)
