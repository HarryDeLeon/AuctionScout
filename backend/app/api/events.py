from __future__ import annotations

import asyncio
from typing import AsyncGenerator

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.events import event_bus

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/{search_id}")
async def stream_events(search_id: int) -> EventSourceResponse:
    queue = event_bus.subscribe(search_id)

    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            while True:
                message = await queue.get()
                yield {"event": message.get("type", "message"), "data": str(message)}
        except asyncio.CancelledError:
            raise
        finally:
            event_bus.unsubscribe(search_id, queue)

    return EventSourceResponse(event_generator())
