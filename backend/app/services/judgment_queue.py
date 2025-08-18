import asyncio
from typing import Any, Dict

_queue: asyncio.Queue | None = None


def get_queue() -> asyncio.Queue:
    global _queue
    if _queue is None:
        _queue = asyncio.Queue()
    return _queue


async def publish(event: Dict[str, Any]):
    q = get_queue()
    await q.put(event)


async def subscribe():
    """Async generator of events."""
    q = get_queue()
    while True:
        ev = await q.get()
        try:
            yield ev
        finally:
            q.task_done()

