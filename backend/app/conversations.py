"""会话/消息数据访问：对齐 conversation.service.ts（含归属校验与标题截断）。"""
import uuid

from fastapi import HTTPException

from .db import get_pool

# 会话标题截取首条提问的最大字符数（对齐 lib/config.ts conversation.titleMaxLength）
TITLE_MAX_LENGTH = 20


def truncate_title(title: str) -> str:
    return title[:TITLE_MAX_LENGTH]


async def assert_ownership(chat_id: str, user_id: str) -> None:
    """会话已存在但不属于当前用户 → 403（对齐 TS 修复过的越权 bug 语义）。"""
    pool = await get_pool()
    row = await pool.fetchrow('SELECT "userId" FROM "Conversation" WHERE id = $1', chat_id)
    if row and row["userId"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")


async def touch_conversation(chat_id: str, user_id: str, title: str) -> None:
    """确保会话存在（不存在则以该用户身份创建），并刷新更新时间。"""
    await assert_ownership(chat_id, user_id)
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO "Conversation" (id, "userId", title, "createdAt", "updatedAt")
        VALUES ($1, $2, $3, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET "updatedAt" = NOW()
        """,
        chat_id,
        user_id,
        truncate_title(title),
    )


async def save_message(chat_id: str, role: str, content: str) -> None:
    """保存一条消息（user / assistant 通用）。"""
    pool = await get_pool()
    await pool.execute(
        'INSERT INTO "Message" (id, "conversationId", role, content, "createdAt") VALUES ($1, $2, $3, $4, NOW())',
        str(uuid.uuid4()),
        chat_id,
        role,
        content,
    )


async def list_conversations(user_id: str) -> list[dict]:
    """当前用户的会话列表（按最近更新倒序），字段与 ConversationDto 对齐。"""
    pool = await get_pool()
    rows = await pool.fetch(
        'SELECT id, title, "updatedAt" FROM "Conversation" WHERE "userId" = $1 ORDER BY "updatedAt" DESC',
        user_id,
    )
    return [
        {"id": r["id"], "title": r["title"], "updatedAt": r["updatedAt"].isoformat()} for r in rows
    ]


async def list_messages(conversation_id: str) -> list[dict]:
    """会话消息历史（按时间正序），字段：id/role/content/createdAt。"""
    pool = await get_pool()
    rows = await pool.fetch(
        'SELECT id, role, content, "createdAt" FROM "Message" WHERE "conversationId" = $1 ORDER BY "createdAt" ASC',
        conversation_id,
    )
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "createdAt": r["createdAt"].isoformat(),
        }
        for r in rows
    ]
