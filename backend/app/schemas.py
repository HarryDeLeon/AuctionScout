from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SearchCreate(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    url: HttpUrl
    min_price: float | None = Field(default=None, ge=0)
    max_price: float | None = Field(default=None, ge=0)
    max_items: int = Field(default=20, ge=1, le=200)
    price_sort_order: Literal["asc", "desc"] = "asc"
    keywords: str | None = None


class SearchSummary(BaseModel):
    id: int
    name: str | None
    url: str
    site: str
    status: str
    progress_done: int
    progress_total: int
    price_sort_order: Literal["asc", "desc"]
    warning: str | None
    error: str | None
    created_at: str
    finished_at: str | None


class ComparableOut(BaseModel):
    id: int
    source: str
    title: str
    price: float
    currency: str
    condition: str | None
    url: str
    image_url: str | None
    listing_type: str
    similarity: float


class ResearchRunOut(BaseModel):
    id: int
    query_text: str
    query_source: str
    status: str
    low: float | None
    high: float | None
    median: float | None
    sample_size: int
    confidence: float
    warning: str | None
    comparables: list[ComparableOut] = []


class LotOut(BaseModel):
    id: int
    lot_number: str | None
    title: str
    description: str | None
    image_url: str | None
    current_bid: float | None
    opening_bid: float | None
    estimate_low: float | None
    estimate_high: float | None
    currency: str
    buyers_premium_pct: float | None
    ends_at: str | None
    lot_url: str | None
    confidence: float
    latest_research: ResearchRunOut | None = None


class SearchDetail(SearchSummary):
    min_price: float | None
    max_price: float | None
    max_items: int
    keywords: str | None
    lots: list[LotOut]


class LotDetail(LotOut):
    research_runs: list[ResearchRunOut]


class SearchCreateResponse(BaseModel):
    search_id: int


class RerunResearchRequest(BaseModel):
    query: str | None = None
    use_image: bool = False
