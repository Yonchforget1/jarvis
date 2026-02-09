"""Chat endpoint: send message to Jarvis, get response with tool calls."""

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.deps import get_current_user
from api.models import ChatRequest, ChatResponse, ToolCallDetail, UserInfo

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Session manager is injected from main.py via app.state
_session_manager = None


def set_session_manager(sm):
    global _session_manager
    _session_manager = sm


@router.post("/chat", response_model=ChatResponse)
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest, user: UserInfo = Depends(get_current_user)):
    session = _session_manager.get_or_create(body.session_id, user.id)

    loop = asyncio.get_event_loop()
    response_text = await loop.run_in_executor(
        None, session.conversation.send, body.message
    )

    raw_calls = session.conversation.get_and_clear_tool_calls()
    tool_calls = [
        ToolCallDetail(
            id=tc["id"],
            name=tc["name"],
            args=tc["args"],
            result=tc["result"],
        )
        for tc in raw_calls
    ]

    return ChatResponse(
        session_id=session.session_id,
        response=response_text,
        tool_calls=tool_calls,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
