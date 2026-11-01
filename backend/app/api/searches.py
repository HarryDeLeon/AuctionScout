from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import build_search_detail, build_search_summary
from app.db import get_db
from app.jobs import enqueue_search
from app.models import Search
from app.schemas import SearchCreate, SearchCreateResponse, SearchDetail, SearchSummary

router = APIRouter(prefix="/api/searches", tags=["searches"])


@router.post("", response_model=SearchCreateResponse, status_code=202)
async def create_search(payload: SearchCreate, db: AsyncSession = Depends(get_db)) -> SearchCreateResponse:
    if payload.min_price is not None and payload.max_price is not None and payload.min_price > payload.max_price:
        raise HTTPException(status_code=400, detail="min_price cannot exceed max_price")

    search = Search(
        name=payload.name.strip() if payload.name else None,
        url=str(payload.url),
        site="pending",
        min_price=payload.min_price,
        max_price=payload.max_price,
        max_items=payload.max_items,
        price_sort_order=payload.price_sort_order,
        keywords=payload.keywords,
        status="queued",
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)
    await enqueue_search(search.id)
    return SearchCreateResponse(search_id=search.id)


@router.delete("/{search_id}", status_code=204)
async def delete_search(search_id: int, db: AsyncSession = Depends(get_db)) -> None:
    search = await db.get(Search, search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    if search.status in {"queued", "fetching", "researching"}:
        raise HTTPException(status_code=409, detail="Search is still running and cannot be deleted yet")
    await db.delete(search)
    await db.commit()


@router.get("/{search_id}", response_model=SearchDetail)
async def get_search(search_id: int, db: AsyncSession = Depends(get_db)) -> SearchDetail:
    search = await db.get(Search, search_id)
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    return await build_search_detail(db, search)


@router.get("", response_model=list[SearchSummary])
async def list_searches(db: AsyncSession = Depends(get_db)) -> list[SearchSummary]:
    rows = (await db.execute(select(Search).order_by(Search.created_at.desc()))).scalars().all()
    return [await build_search_summary(row) for row in rows]
