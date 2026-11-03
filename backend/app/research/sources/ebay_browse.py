from __future__ import annotations

import httpx

from app.config import settings
from app.research.sources.base import ComparableRecord, SourceConfigurationError


class EbayBrowseSource:
    async def search(
        self,
        query: str,
        use_image: bool = False,
        image_url: str | None = None,
    ) -> list[ComparableRecord]:
        del use_image, image_url
        if not settings.ebay_access_token:
            raise SourceConfigurationError("eBay access token is not configured")

        headers = {
            "Authorization": f"Bearer {settings.ebay_access_token}",
            "X-EBAY-C-MARKETPLACE-ID": settings.ebay_marketplace_id,
        }
        params = {
            "q": query,
            "limit": "12",
            "filter": "buyingOptions:{AUCTION|FIXED_PRICE}",
        }

        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(settings.ebay_browse_base_url, headers=headers, params=params)
            response.raise_for_status()
            payload = response.json()

        result: list[ComparableRecord] = []
        for item in payload.get("itemSummaries", []):
            price_obj = item.get("price") or {}
            value = price_obj.get("value")
            if value is None:
                continue
            result.append(
                ComparableRecord(
                    source="ebay_browse",
                    title=item.get("title", "eBay listing"),
                    price=float(value),
                    currency=price_obj.get("currency", "CAD"),
                    condition=item.get("condition"),
                    url=item.get("itemWebUrl", ""),
                    image_url=(item.get("image") or {}).get("imageUrl"),
                    listing_type="active_ask",
                    similarity=0.7,
                )
            )
        return result
