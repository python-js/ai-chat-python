"""系统配置：默认值在代码，数据库只存覆盖值（值等于默认则删行）。

读取带进程内 TTL 缓存（多实例部署下最大不一致窗口为 CACHE_TTL 秒）；
保存时逐项校验 + diff。key 命名：<组>.<项>。
"""
import json
import time

from .config import settings
from .db import get_pool
from .prompts import CONTEXT_PLACEHOLDER, DEFAULT_CHAT_SYSTEM, DEFAULT_RAG_SYSTEM

# 缓存有效期（秒）：保存后仅失效本实例缓存，多实例下其他实例最多延迟该时长生效
CACHE_TTL = 30

# 全部配置项的默认值（库内无覆盖值时使用；与默认值相同的覆盖会在保存时被删除）
DEFAULTS: dict = {
    "prompt.rag_system": DEFAULT_RAG_SYSTEM,
    "prompt.chat_system": DEFAULT_CHAT_SYSTEM,
    "llm.model": settings.llm_model,
    "llm.temperature": None,  # None = 不传该参数，走百炼默认
    "llm.max_tokens": None,
    "llm.enable_search": True,
    "rag.distance_threshold": settings.rag_distance_threshold,
    "rag.top_k": 5,
    "chat.title_max_length": 20,
    "chat.default_mode": "chat",
    "chat.welcome_text": "有什么可以帮你的？",
    "chat.empty_context_text": "（未找到相关文档内容）",
}

_cache: dict | None = None
_cache_at: float = 0.0


def _is_number(value, low: float, high: float) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and low <= value <= high


def _validate(key: str, value) -> None:
    """逐项校验，非法值抛 ValueError（路由层转 400）。"""
    if key not in DEFAULTS:
        raise ValueError(f"未知配置项：{key}")

    if key in ("prompt.rag_system", "prompt.chat_system", "llm.model", "chat.welcome_text", "chat.empty_context_text"):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{key} 需要非空文本")
        if key == "prompt.rag_system" and CONTEXT_PLACEHOLDER not in value:
            raise ValueError(f"知识库提示词必须包含 {CONTEXT_PLACEHOLDER} 占位符")
    elif key == "chat.default_mode":
        if value not in ("rag", "chat"):
            raise ValueError("默认对话模式只能是 rag 或 chat")
    elif key == "llm.enable_search":
        if not isinstance(value, bool):
            raise ValueError("联网搜索开关需要布尔值（true/false）")
    elif key == "llm.temperature":
        if value is not None and not _is_number(value, 0, 2):
            raise ValueError("temperature 需要是 0~2 的数字（或留空）")
    elif key == "llm.max_tokens":
        if value is not None and not _is_number(value, 1, 32768):
            raise ValueError("max_tokens 需要是 1~32768 的数字（或留空）")
    elif key == "rag.distance_threshold":
        if not _is_number(value, 0, 2):
            raise ValueError("距离阈值需要是 0~2 的数字")
    elif key == "rag.top_k":
        if not _is_number(value, 1, 20):
            raise ValueError("top_k 需要是 1~20 的数字")
    elif key == "chat.title_max_length":
        if not _is_number(value, 1, 100):
            raise ValueError("标题截断长度需要是 1~100 的数字")


def invalidate_cache() -> None:
    """失效本实例缓存（保存后调用；多实例下其他实例最多 CACHE_TTL 后生效）。"""
    global _cache
    _cache = None


async def load_config() -> dict:
    """完整配置 = 默认值 + 库内覆盖值（带 TTL 缓存；返回新 dict 防止调用方修改共享缓存）。"""
    global _cache, _cache_at
    now = time.monotonic()
    if _cache is not None and now - _cache_at < CACHE_TTL:
        return dict(_cache)
    pool = await get_pool()
    rows = await pool.fetch('SELECT key, value FROM "AppConfig"')
    values = dict(DEFAULTS)
    for row in rows:
        key = row["key"]
        if key not in DEFAULTS:
            continue  # 已废弃 key 的残留行，忽略
        try:
            values[key] = json.loads(row["value"])
        except json.JSONDecodeError:
            continue  # 脏数据回退默认值
    _cache = values
    _cache_at = now
    return dict(values)


async def save_config(new_values: dict) -> dict:
    """校验 + diff 保存：值等于默认 → 删行；否则 upsert。返回保存后的完整配置。"""
    if not isinstance(new_values, dict) or not new_values:
        raise ValueError("配置内容为空")
    for key, value in new_values.items():
        _validate(key, value)

    pool = await get_pool()
    for key, value in new_values.items():
        if value == DEFAULTS[key]:
            await pool.execute('DELETE FROM "AppConfig" WHERE key = $1', key)
        else:
            await pool.execute(
                'INSERT INTO "AppConfig" (key, value, "updatedAt") VALUES ($1, $2, NOW()) '
                'ON CONFLICT (key) DO UPDATE SET value = $2, "updatedAt" = NOW()',
                key,
                json.dumps(value, ensure_ascii=False),
            )
    invalidate_cache()
    return await load_config()
