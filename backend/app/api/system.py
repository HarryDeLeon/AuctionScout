from __future__ import annotations

from fastapi import APIRouter

from app.adapters.registry import registry
from app.config import settings

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/adapters")
async def adapters() -> dict[str, list[str]]:
    return {"supported": registry.list_supported()}


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "sources": {
            "ebay_browse_configured": bool(settings.ebay_access_token),
            "ebay_web_fallback_enabled": True,
            "duckduckgo_price_enabled": True,
        },
        "llm_query_builder_enabled": settings.enable_llm_query_builder,
        "default_currency": settings.default_currency,
    }
