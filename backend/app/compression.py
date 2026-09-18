"""会话上下文压缩：把较早的消息（含旧摘要）滚动压缩为一份新摘要。

语义（与设计定稿一致）：
- 压缩范围 = 上次压缩点之后、最近 KEEP_RECENT 条之前的消息（旧摘要并入输入）
- 摘要输入受 llm.context_max_chars 预算约束，从最早顺序纳入；
  装不下的消息留在活跃上下文，等待下次压缩（不会出现"已跨过压缩点却未进入摘要"的丢失）
- 成功后更新 Conversation.summary / summaryUpToId，此后上下文 = 摘要 + 压缩点之后消息
"""
import logging

from .app_config import load_config
from .conversations import get_conversation_meta, list_messages, save_summary
from .llm import complete_chat

logger = logging.getLogger(__name__)

# 压缩时保留最近的消息条数（不参与压缩，保持近期对话原样）
KEEP_RECENT = 4


async def compress_conversation(conversation_id: str) -> dict | None:
    """执行一次手动压缩；会话不存在返回 None。

    返回 {"summary": str, "compressedCount": int} 或 {"skipped": True, "reason": str}。
    """
    meta = await get_conversation_meta(conversation_id)
    if meta is None:
        return None
    messages = await list_messages(conversation_id)
    # 压缩点过滤：只处理上次压缩点之后的消息（压缩点消息查不到时保守处理全部）
    if meta["summaryUpToId"]:
        for i, m in enumerate(messages):
            if m["id"] == meta["summaryUpToId"]:
                messages = messages[i + 1 :]
                break
    # 保留最近 KEEP_RECENT 条不压缩；空 content 消息（纯卡片）跳过
    candidates = messages[:-KEEP_RECENT] if len(messages) > KEEP_RECENT else []
    candidates = [m for m in candidates if m["content"]]

    config = await load_config()
    # 摘要输入预算：旧摘要 + 待压缩消息，按从最早顺序纳入直到预算
    budget = config["llm.context_max_chars"]
    used = len(meta["summary"] or "")
    selected: list[dict] = []
    for m in candidates:
        if used + len(m["content"]) > budget:
            break
        selected.append(m)
        used += len(m["content"])
    if not selected:
        return {"skipped": True, "reason": "暂无可压缩的内容"}

    lines: list[str] = []
    if meta["summary"]:
        lines.append(f"【已有摘要】\n{meta['summary']}")
    lines.extend(f"{'用户' if m['role'] == 'user' else '助手'}：{m['content']}" for m in selected)
    transcript = "\n\n".join(lines)

    summary = (
        await complete_chat(
            [{"role": "user", "content": transcript}],
            system=config["prompt.summary"],
            model=config["llm.model"],
            temperature=0.3,  # 摘要任务低随机性
        )
    ).strip()
    if not summary:
        raise RuntimeError("摘要生成结果为空")

    await save_summary(conversation_id, summary, selected[-1]["id"])
    logger.info("会话 %s 已压缩 %d 条消息", conversation_id, len(selected))
    return {"summary": summary, "compressedCount": len(selected)}
