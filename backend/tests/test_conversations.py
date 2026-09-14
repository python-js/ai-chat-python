"""会话逻辑测试：标题截断（对齐 conversation.service.test.ts）+ 归属校验（mock 数据层）。"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.conversations import TITLE_MAX_LENGTH, assert_ownership, delete_conversation, truncate_title


def test_truncate_title_short_unchanged():
    assert truncate_title("如何退款") == "如何退款"


def test_truncate_title_exact_max_unchanged():
    title = "标" * TITLE_MAX_LENGTH
    assert truncate_title(title) == title


def test_truncate_title_long_cut():
    title = "标" * (TITLE_MAX_LENGTH + 50)
    result = truncate_title(title)
    assert len(result) == TITLE_MAX_LENGTH
    assert result == "标" * TITLE_MAX_LENGTH


def test_truncate_title_empty():
    assert truncate_title("") == ""


@pytest.mark.asyncio
async def test_assert_ownership_403_when_not_owner():
    mock_pool = AsyncMock()
    mock_pool.fetchrow.return_value = {"userId": "other-user"}
    with patch("app.conversations.get_pool", return_value=mock_pool):
        with pytest.raises(HTTPException) as exc:
            await assert_ownership("chat-1", "my-user")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_assert_ownership_ok_when_owner():
    mock_pool = AsyncMock()
    mock_pool.fetchrow.return_value = {"userId": "my-user"}
    with patch("app.conversations.get_pool", return_value=mock_pool):
        await assert_ownership("chat-1", "my-user")


@pytest.mark.asyncio
async def test_assert_ownership_ok_when_not_exists():
    # 会话不存在 → 允许创建（upsert 语义）
    mock_pool = AsyncMock()
    mock_pool.fetchrow.return_value = None
    with patch("app.conversations.get_pool", return_value=mock_pool):
        await assert_ownership("chat-1", "my-user")


@pytest.mark.asyncio
async def test_delete_conversation_true_when_exists():
    # 第一次 fetchrow：归属查询；第二次：DELETE RETURNING id
    mock_pool = AsyncMock()
    mock_pool.fetchrow.side_effect = [{"userId": "my-user"}, {"id": "chat-1"}]
    with patch("app.conversations.get_pool", return_value=mock_pool):
        assert await delete_conversation("chat-1", "my-user") is True


@pytest.mark.asyncio
async def test_delete_conversation_false_when_missing():
    mock_pool = AsyncMock()
    mock_pool.fetchrow.side_effect = [None, None]
    with patch("app.conversations.get_pool", return_value=mock_pool):
        assert await delete_conversation("chat-1", "my-user") is False


@pytest.mark.asyncio
async def test_delete_conversation_403_when_not_owner():
    mock_pool = AsyncMock()
    mock_pool.fetchrow.return_value = {"userId": "other-user"}
    with patch("app.conversations.get_pool", return_value=mock_pool):
        with pytest.raises(HTTPException) as exc:
            await delete_conversation("chat-1", "my-user")
    assert exc.value.status_code == 403
