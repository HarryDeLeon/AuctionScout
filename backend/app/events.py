from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._queues: dict[int, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    def subscribe(self, search_id: int) -> asyncio.Queue[dict[str, Any]]:
        q: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues[search_id].append(q)
        return q

    def unsubscribe(self, search_id: int, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if search_id in self._queues and queue in self._queues[search_id]:
            self._queues[search_id].remove(queue)

    async def publish(self, search_id: int, event: dict[str, Any]) -> None:
        for queue in self._queues.get(search_id, []):
            await queue.put(event)


event_bus = EventBus()
