from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.helpers import build_lot_detail
from app.db import get_db
from app.jobs import rerun_lot_research
from app.models import Lot
from app.schemas import LotDetail, RerunResearchRequest

router = APIRouter(prefix="/api/lots", tags=["lots"])


@router.get("/{lot_id}", response_model=LotDetail)
async def get_lot(lot_id: int, db: AsyncSession = Depends(get_db)) -> LotDetail:
    lot = await db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    return await build_lot_detail(db, lot)


@router.post("/{lot_id}/research", response_model=LotDetail)
async def rerun_research(lot_id: int, payload: RerunResearchRequest, db: AsyncSession = Depends(get_db)) -> LotDetail:
    lot = await db.get(Lot, lot_id)
    if not lot:
        raise HTTPException(status_code=404, detail="Lot not found")
    await rerun_lot_research(db, lot_id=lot_id, query=payload.query, use_image=payload.use_image)
    updated_lot = await db.get(Lot, lot_id)
    return await build_lot_detail(db, updated_lot)
