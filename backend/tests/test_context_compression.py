"""上下文管理新功能测试：预算裁剪（chat.trim_by_budget）、错误友好化、会话压缩（compression）。"""
from unittest.mock import AsyncMock, patch

import pytest

from app.chat import _friendly_error, trim_by_budget
from app.compression import KEEP_RECENT, compress_conversation
from app.conversations import list_context_messages


# ---------- trim_by_budget（输入预算裁剪） ----------

def _msgs(*pairs):
    return [{"role": r, "content": c} for r, c in pairs]


def test_trim_by_budget_within_limit_unchanged():
    msgs = _msgs(("user", "a" * 10), ("assistant", "b" * 10))
    assert trim_by_budget(msgs, 100) == msgs


def test_trim_by_budget_drops_earliest():
    msgs = _msgs(("user", "a" * 10), ("assistant", "b" * 10), ("user", "c" * 10))
    assert trim_by_budget(msgs, 25) == [
        {"role": "assistant", "content": "b" * 10},
        {"role": "user", "content": "c" * 10},
    ]


def test_trim_by_budget_keeps_last_when_oversized():
    # 单条也超预算：至少保留最后一条（不能丢空导致请求无消息）
    msgs = _msgs(("user", "a" * 100), ("assistant", "b" * 100))
    assert trim_by_budget(msgs, 50) == [{"role": "assistant", "content": "b" * 100}]


def test_trim_by_budget_empty():
    assert trim_by_budget([], 10) == []


# ---------- _friendly_error（超限友好化） ----------

class _FakeResponse:
    def __init__(self, status_code, text):
        self.status_code = status_code
        self.text = text


def test_friendly_error_context_overflow():
    e = Exception("Client error '400 Bad Request'")
    e.response = _FakeResponse(400, "Range of input length should be [1, 129024]")
    assert _friendly_error(e) == "当前会话上下文过长，建议压缩上下文或开启新会话"


def test_friendly_error_other_400_kept():
    e = Exception("bad request")
    e.response = _FakeResponse(400, "some other error")
    assert _friendly_error(e) == "bad request"


def test_friendly_error_no_response():
    assert _friendly_error(RuntimeError("boom")) == "boom"


# ---------- list_context_messages（压缩点过滤） ----------

@pytest.mark.asyncio
async def test_list_context_messages_filters_after_summary_point():
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": ""},  # 空 content（纯卡片）被过滤
    ]
    with patch("app.conversations.get_pool", return_value=mock_pool):
        result = await list_context_messages("chat-1", "point-1")
    assert result == [{"role": "user", "content": "hello"}]
    # pool.fetch(sql, conversation_id, summary_up_to_id)：业务参数从索引 1 开始
    args = mock_pool.fetch.await_args.args
    assert args[1] == "chat-1" and args[2] == "point-1"
    assert '"createdAt" >' in args[0]  # 压缩点过滤条件存在


@pytest.mark.asyncio
async def test_list_context_messages_without_point_fetches_all():
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [{"role": "user", "content": "hi"}]
    with patch("app.conversations.get_pool", return_value=mock_pool):
        result = await list_context_messages("chat-1", None)
    assert result == [{"role": "user", "content": "hi"}]
    args = mock_pool.fetch.await_args.args
    assert len(args) == 2 and args[1] == "chat-1"  # 无压缩点：不带过滤参数
    assert '"createdAt" >' not in args[0]


# ---------- compress_conversation（手动压缩） ----------

def _cfg(budget=60000):
    return {"llm.context_max_chars": budget, "prompt.summary": "总结", "llm.model": "qwen-turbo"}


def _messages(n):
    """构造 n 条交替消息（content 为 2 个汉字 + 序号，共 3 字符）。"""
    return [
        {"id": f"m{i}", "role": "user" if i % 2 == 0 else "assistant", "content": f"内容{i}"}
        for i in range(n)
    ]


@pytest.mark.asyncio
async def test_compress_missing_conversation_returns_none():
    with patch("app.compression.get_conversation_meta", new=AsyncMock(return_value=None)):
        assert await compress_conversation("chat-x") is None


@pytest.mark.asyncio
async def test_compress_skipped_when_too_few_messages():
    with (
        patch(
            "app.compression.get_conversation_meta",
            new=AsyncMock(return_value={"summary": None, "summaryUpToId": None}),
        ),
        patch("app.compression.list_messages", new=AsyncMock(return_value=_messages(4))),
    ):
        assert await compress_conversation("chat-x") == {"skipped": True, "reason": "暂无可压缩的内容"}


@pytest.mark.asyncio
async def test_compress_happy_path_saves_summary_point():
    messages = _messages(10)  # 可压缩 = 前 6 条（保留最近 KEEP_RECENT 条）
    save = AsyncMock()
    complete = AsyncMock(return_value="  摘要内容  ")
    with (
        patch(
            "app.compression.get_conversation_meta",
            new=AsyncMock(return_value={"summary": None, "summaryUpToId": None}),
        ),
        patch("app.compression.list_messages", new=AsyncMock(return_value=messages)),
        patch("app.compression.load_config", new=AsyncMock(return_value=_cfg())),
        patch("app.compression.complete_chat", new=complete),
        patch("app.compression.save_summary", new=save),
    ):
        result = await compress_conversation("chat-x")
    assert result == {"summary": "摘要内容", "compressedCount": 10 - KEEP_RECENT}
    save.assert_awaited_once_with("chat-x", "摘要内容", messages[10 - KEEP_RECENT - 1]["id"])
    transcript = complete.await_args.args[0][0]["content"]
    assert "内容0" in transcript and "内容5" in transcript
    assert "内容6" not in transcript  # 保留窗口内的消息不参与压缩


@pytest.mark.asyncio
async def test_compress_respects_summary_point_and_existing_summary():
    messages = _messages(12)
    with (
        patch(
            "app.compression.get_conversation_meta",
            new=AsyncMock(return_value={"summary": "旧摘要", "summaryUpToId": messages[3]["id"]}),
        ),
        patch("app.compression.list_messages", new=AsyncMock(return_value=messages)),
        patch("app.compression.load_config", new=AsyncMock(return_value=_cfg())),
        patch("app.compression.complete_chat", new=AsyncMock(return_value="新摘要")),
        patch("app.compression.save_summary", new=AsyncMock()) as save,
    ):
        result = await compress_conversation("chat-x")
    # 压缩点之后 8 条 → 保留 4 → 压缩 m4..m7 共 4 条
    assert result == {"summary": "新摘要", "compressedCount": 4}
    save.assert_awaited_once_with("chat-x", "新摘要", messages[7]["id"])


@pytest.mark.asyncio
async def test_compress_transcript_merges_existing_summary():
    messages = _messages(12)
    complete = AsyncMock(return_value="新摘要")
    with (
        patch(
            "app.compression.get_conversation_meta",
            new=AsyncMock(return_value={"summary": "旧摘要", "summaryUpToId": messages[3]["id"]}),
        ),
        patch("app.compression.list_messages", new=AsyncMock(return_value=messages)),
        patch("app.compression.load_config", new=AsyncMock(return_value=_cfg())),
        patch("app.compression.complete_chat", new=complete),
        patch("app.compression.save_summary", new=AsyncMock()),
    ):
        await compress_conversation("chat-x")
    transcript = complete.await_args.args[0][0]["content"]
    assert "【已有摘要】" in transcript and "旧摘要" in transcript
    assert "内容4" in transcript and "内容7" in transcript
    assert "内容3" not in transcript  # 压缩点之前的消息不参与


@pytest.mark.asyncio
async def test_compress_budget_takes_earliest_prefix_only():
    messages = _messages(10)  # 每条 3 字符
    with (
        patch(
            "app.compression.get_conversation_meta",
            new=AsyncMock(return_value={"summary": None, "summaryUpToId": None}),
        ),
        patch("app.compression.list_messages", new=AsyncMock(return_value=messages)),
        patch("app.compression.load_config", new=AsyncMock(return_value=_cfg(budget=8))),
        patch("app.compression.complete_chat", new=AsyncMock(return_value="摘要")),
        patch("app.compression.save_summary", new=AsyncMock()) as save,
    ):
        result = await compress_conversation("chat-x")
    # 预算 8：仅前 2 条（3+3=6）可纳入，其余留待下次压缩
    assert result == {"summary": "摘要", "compressedCount": 2}
    save.assert_awaited_once_with("chat-x", "摘要", messages[1]["id"])


@pytest.mark.asyncio
async def test_compress_empty_summary_raises():
    messages = _messages(10)
    with (
        patch(
            "app.compression.get_conversation_meta",
            new=AsyncMock(return_value={"summary": None, "summaryUpToId": None}),
        ),
        patch("app.compression.list_messages", new=AsyncMock(return_value=messages)),
        patch("app.compression.load_config", new=AsyncMock(return_value=_cfg())),
        patch("app.compression.complete_chat", new=AsyncMock(return_value="   ")),
        patch("app.compression.save_summary", new=AsyncMock()) as save,
    ):
        with pytest.raises(RuntimeError):
            await compress_conversation("chat-x")
    save.assert_not_awaited()
