"""会话/消息数据访问：对齐 conversation.service.ts（含归属校验与标题截断）。"""
import json
import uuid

from fastapi import HTTPException

from .app_config import load_config
from .db import get_pool

# 会话标题截取首条提问的默认最大字符数（运行时以系统配置 chat.title_max_length 为准）
TITLE_MAX_LENGTH = 20


def truncate_title(title: str, max_length: int = TITLE_MAX_LENGTH) -> str:
    return title[:max_length]


async def assert_ownership(chat_id: str, user_id: str) -> None:
    """会话已存在但不属于当前用户 → 403（对齐 TS 修复过的越权 bug 语义）。"""
    pool = await get_pool()
    row = await pool.fetchrow('SELECT "userId" FROM "Conversation" WHERE id = $1', chat_id)
    if row and row["userId"] != user_id:
        raise HTTPException(status_code=403, detail="无权访问该会话")


async def touch_conversation(chat_id: str, user_id: str, title: str) -> None:
    """确保会话存在（不存在则以该用户身份创建），并刷新更新时间。"""
    await assert_ownership(chat_id, user_id)
    config = await load_config()
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO "Conversation" (id, "userId", title, "createdAt", "updatedAt")
        VALUES ($1, $2, $3, NOW(), NOW())
        ON CONFLICT (id) DO UPDATE SET "updatedAt" = NOW()
        """,
        chat_id,
        user_id,
        truncate_title(title, config["chat.title_max_length"]),
    )


async def save_message(chat_id: str, role: str, content: str, card_data: list[dict] | None = None) -> None:
    """保存一条消息（user / assistant 通用）；card_data 为助手消息附带的结构化卡片（可选）。"""
    pool = await get_pool()
    await pool.execute(
        'INSERT INTO "Message" (id, "conversationId", role, content, "cardData", "createdAt") '
        "VALUES ($1, $2, $3, $4, $5::jsonb, NOW())",
        str(uuid.uuid4()),
        chat_id,
        role,
        content,
        json.dumps(card_data, ensure_ascii=False) if card_data else None,
    )


async def delete_conversation(conversation_id: str, user_id: str) -> bool:
    """删除会话及其消息（Message 经外键 ON DELETE CASCADE 一并删除）。返回会话是否存在。"""
    await assert_ownership(conversation_id, user_id)
    pool = await get_pool()
    row = await pool.fetchrow('DELETE FROM "Conversation" WHERE id = $1 RETURNING id', conversation_id)
    return row is not None


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
    """会话消息历史（按时间正序），字段：id/role/content/cardData/createdAt。"""
    pool = await get_pool()
    rows = await pool.fetch(
        'SELECT id, role, content, "cardData", "createdAt" FROM "Message" WHERE "conversationId" = $1 ORDER BY "createdAt" ASC',
        conversation_id,
    )
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            # asyncpg 对 jsonb 返回字符串，解析为对象给前端（NULL 保持 None）
            "cardData": json.loads(r["cardData"]) if r["cardData"] else None,
            "createdAt": r["createdAt"].isoformat(),
        }
        for r in rows
    ]


async def get_conversation_meta(conversation_id: str) -> dict | None:
    """会话摘要与压缩点（NULL = 未压缩）；会话不存在返回 None。"""
    pool = await get_pool()
    row = await pool.fetchrow(
        'SELECT "summary", "summaryUpToId" FROM "Conversation" WHERE id = $1', conversation_id
    )
    if row is None:
        return None
    return {"summary": row["summary"], "summaryUpToId": row["summaryUpToId"]}


async def save_summary(conversation_id: str, summary: str, summary_up_to_id: str) -> None:
    """保存压缩结果：摘要 + 压缩点（被压缩的最后一条消息 id）。"""
    pool = await get_pool()
    await pool.execute(
        'UPDATE "Conversation" SET "summary" = $2, "summaryUpToId" = $3, "updatedAt" = NOW() '
        "WHERE id = $1",
        conversation_id,
        summary,
        summary_up_to_id,
    )


async def list_context_messages(conversation_id: str, summary_up_to_id: str | None) -> list[dict]:
    """模型上下文用消息（按时间正序，仅 role/content）：有压缩点时只取其后消息。

    消息 id 由后端落库时生成（与前端 id 无关），压缩点过滤只信任 DB 时间序。
    """
    pool = await get_pool()
    if summary_up_to_id:
        rows = await pool.fetch(
            'SELECT role, content FROM "Message" WHERE "conversationId" = $1 '
            'AND "createdAt" > (SELECT "createdAt" FROM "Message" WHERE id = $2) '
            'ORDER BY "createdAt" ASC',
            conversation_id,
            summary_up_to_id,
        )
    else:
        rows = await pool.fetch(
            'SELECT role, content FROM "Message" WHERE "conversationId" = $1 ORDER BY "createdAt" ASC',
            conversation_id,
        )
    return [{"role": r["role"], "content": r["content"]} for r in rows if r["content"]]
