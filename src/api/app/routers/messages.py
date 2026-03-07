"""Agent message endpoints — list and stream agent conversation transcript."""

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

router = APIRouter(tags=["messages"])

# TODO: Wire to an in-memory message store (similar pattern to event_store)
_messages: list[dict] = []


@router.get("/agent-messages")
async def get_agent_messages():
    """Return all agent chat messages."""
    return _messages


@router.get("/agent-messages/stream")
async def stream_agent_messages():
    """SSE stream of agent messages as they are produced."""

    async def message_generator():
        # TODO: implement subscriber pattern (mirroring event_store.subscribe)
        yield {"data": "connected"}

    return EventSourceResponse(message_generator())
