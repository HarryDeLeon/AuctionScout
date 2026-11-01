import asyncio
import os

import pytest

from app.adapters.liveauctioneers import LiveAuctioneersAdapter
from app.adapters.urbanauctions import UrbanAuctionsAdapter


def _run_live_enabled() -> bool:
    return os.getenv("RUN_LIVE_ADAPTER_TESTS", "").strip().lower() in {"1", "true", "yes"}


def _require_live() -> None:
    if not _run_live_enabled():
        pytest.skip("Live tests disabled. Set RUN_LIVE_ADAPTER_TESTS=1 to enable.")


def _require_url(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        pytest.skip(f"Missing {name}; skipping live smoke test.")
    return value


@pytest.mark.live
def test_live_liveauctioneers_adapter_smoke():
    _require_live()
    url = _require_url("LIVE_LIVEAUCTIONEERS_URL")
    adapter = LiveAuctioneersAdapter()
    lots = asyncio.run(adapter.fetch_lots(url, max_items=5))
    assert len(lots) > 0


@pytest.mark.live
def test_live_urbanauctions_adapter_smoke():
    _require_live()
    url = _require_url("LIVE_URBANAUCTIONS_URL")
    adapter = UrbanAuctionsAdapter()
    lots = asyncio.run(adapter.fetch_lots(url, max_items=5))
    assert len(lots) > 0
