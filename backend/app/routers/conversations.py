"""会话列表 / 消息历史 / 删除（方案 A 下沉，Node 不再直读写 Conversation/Message 表）。"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ..auth import get_user_id
from ..conversations import assert_ownership, delete_conversation, list_conversations, list_messages

router = APIRouter(prefix="/api")


@router.get("/conversations")
async def conversations(user_id: Annotated[str, Depends(get_user_id)]):
    return await list_conversations(user_id)


@router.delete("/conversations/{conversation_id}")
async def remove_conversation(
    conversation_id: str,
    user_id: Annotated[str, Depends(get_user_id)],
):
    # 归属校验在 delete_conversation 内（非本人 403）；会话不存在 → 404
    if not await delete_conversation(conversation_id, user_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"ok": True}


@router.get("/conversations/{conversation_id}/messages")
async def messages(conversation_id: str, user_id: Annotated[str, Depends(get_user_id)]):
    # 归属校验：非本人会话 → 403
    await assert_ownership(conversation_id, user_id)
    return await list_messages(conversation_id)
