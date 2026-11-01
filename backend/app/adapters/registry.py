from __future__ import annotations

from urllib.parse import urlparse

from app.adapters.generic import GenericAdapter
from app.adapters.liveauctioneers import LiveAuctioneersAdapter
from app.adapters.urbanauctions import UrbanAuctionsAdapter


class AdapterRegistry:
    def __init__(self) -> None:
        self.adapters = [LiveAuctioneersAdapter(), UrbanAuctionsAdapter(), GenericAdapter()]

    def resolve(self, url: str):
        host = urlparse(url).netloc
        for adapter in self.adapters:
            for pattern in adapter.url_patterns:
                if pattern.search(host) or pattern.search(url):
                    return adapter
        return GenericAdapter()

    def list_supported(self) -> list[str]:
        return [adapter.name for adapter in self.adapters if adapter.name != "generic"]


registry = AdapterRegistry()
