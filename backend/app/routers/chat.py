"""POST /api/chat：SSE 流式聊天（浏览器经 Next rewrites 代理访问）。"""
from typing import Annotated

from fastapi import APIRouter, Body, Depends

from ..auth import get_user_id
from ..chat import CHAT_MODES, stream_chat_sse

router = APIRouter(prefix="/api")


@router.post("/chat")
async def chat(
    user_id: Annotated[str, Depends(get_user_id)],
    body: dict = Body(...),
):
    # mode 缺省为 chat（与后端「不传 mode 即闲聊」语义一致）；非法值兜底 chat
    mode = body.get("mode")
    mode = mode if mode in CHAT_MODES else "chat"
    return await stream_chat_sse(
        user_id=user_id,
        chat_id=body.get("id"),
        messages=body.get("messages") or [],
        mode=mode,
    )
