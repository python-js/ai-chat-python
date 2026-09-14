"""会话列表 / 消息历史（方案 A 下沉，Node 不再直读写 Conversation/Message 表）。"""
from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth import get_user_id
from ..conversations import assert_ownership, list_conversations, list_messages

router = APIRouter(prefix="/api")


@router.get("/conversations")
async def conversations(user_id: Annotated[str, Depends(get_user_id)]):
    return await list_conversations(user_id)


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: str, user_id: Annotated[str, Depends(get_user_id)]):
    # 归属校验：非本人会话 → 403
    await assert_ownership(conversation_id, user_id)
    return await list_messages(conversation_id)
