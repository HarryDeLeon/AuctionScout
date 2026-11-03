from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import build_search_detail, build_search_summary
from app.db import get_db
from app.imports.csv_lots import parse_lots_csv
from app.jobs import enqueue_manual_search, enqueue_search
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


@router.post("/import-csv", response_model=SearchCreateResponse, status_code=202)
async def import_search_csv(
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    min_price: float | None = Form(default=None),
    max_price: float | None = Form(default=None),
    max_items: int = Form(default=20),
    price_sort_order: str = Form(default="asc"),
    keywords: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
) -> SearchCreateResponse:
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(status_code=400, detail="min_price cannot exceed max_price")
    if max_items < 1 or max_items > 200:
        raise HTTPException(status_code=400, detail="max_items must be between 1 and 200")
    if price_sort_order not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="price_sort_order must be 'asc' or 'desc'")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="CSV file is empty")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

    parsed = parse_lots_csv(text, max_items=max_items * 3)
    if not parsed.lots:
        detail = "; ".join(parsed.warnings) if parsed.warnings else "No valid lots found in CSV"
        raise HTTPException(status_code=400, detail=detail)

    search = Search(
        name=name.strip() if name else None,
        url=f"manual://{file.filename or 'import.csv'}",
        site="manual_csv",
        min_price=min_price,
        max_price=max_price,
        max_items=max_items,
        price_sort_order=price_sort_order,
        keywords=keywords,
        status="queued",
        warning=("; ".join(parsed.warnings[:5]) if parsed.warnings else None),
    )
    db.add(search)
    await db.commit()
    await db.refresh(search)

    await enqueue_manual_search(search.id, parsed.lots, parsed.warnings)
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
