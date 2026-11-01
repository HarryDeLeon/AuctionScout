from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Search(Base):
    __tablename__ = "searches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    site: Mapped[str] = mapped_column(String(100), nullable=False)
    min_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_items: Mapped[int] = mapped_column(Integer, nullable=False)
    price_sort_order: Mapped[str] = mapped_column(String(4), nullable=False, default="asc")
    keywords: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    progress_done: Mapped[int] = mapped_column(Integer, default=0)
    progress_total: Mapped[int] = mapped_column(Integer, default=0)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lots: Mapped[list[Lot]] = relationship(back_populates="search", cascade="all, delete-orphan")


class Lot(Base):
    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    search_id: Mapped[int] = mapped_column(ForeignKey("searches.id"), nullable=False, index=True)
    lot_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    opening_bid: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimate_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimate_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(5), default="CAD")
    buyers_premium_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    ends_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.7)

    search: Mapped[Search] = relationship(back_populates="lots")
    research_runs: Mapped[list[ResearchRun]] = relationship(back_populates="lot", cascade="all, delete-orphan")


class ResearchRun(Base):
    __tablename__ = "research_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"), nullable=False, index=True)
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    query_source: Mapped[str] = mapped_column(String(20), default="auto")
    status: Mapped[str] = mapped_column(String(30), default="done")
    low: Mapped[float | None] = mapped_column(Float, nullable=True)
    high: Mapped[float | None] = mapped_column(Float, nullable=True)
    median: Mapped[float | None] = mapped_column(Float, nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    warning: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    lot: Mapped[Lot] = relationship(back_populates="research_runs")
    comparables: Mapped[list[Comparable]] = relationship(back_populates="research_run", cascade="all, delete-orphan")


class Comparable(Base):
    __tablename__ = "comparables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    research_run_id: Mapped[int] = mapped_column(ForeignKey("research_runs.id"), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False, default="CAD")
    condition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    listing_type: Mapped[str] = mapped_column(String(30), default="active_ask")
    similarity: Mapped[float] = mapped_column(Float, default=0.5)

    research_run: Mapped[ResearchRun] = relationship(back_populates="comparables")
