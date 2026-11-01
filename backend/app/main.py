from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app.api.events import router as events_router
from app.api.lots import router as lots_router
from app.api.searches import router as searches_router
from app.api.system import router as system_router
from app.config import settings
from app.db import engine
from app.models import Base


def _ensure_search_columns(sync_conn) -> None:
    inspector = inspect(sync_conn)
    columns = {col["name"] for col in inspector.get_columns("searches")}
    if "name" not in columns:
        sync_conn.exec_driver_sql("ALTER TABLE searches ADD COLUMN name VARCHAR(160)")
    if "price_sort_order" not in columns:
        sync_conn.exec_driver_sql("ALTER TABLE searches ADD COLUMN price_sort_order VARCHAR(4) DEFAULT 'asc'")


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_search_columns)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system_router)
app.include_router(searches_router)
app.include_router(lots_router)
app.include_router(events_router)
