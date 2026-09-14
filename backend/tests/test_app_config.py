"""系统配置测试：缓存合并、diff 保存、校验（mock 数据层）。"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app import app_config
from app.app_config import DEFAULTS, load_config, save_config


@pytest.fixture(autouse=True)
def _clear_cache():
    # 清空进程内缓存，避免用例间互相污染
    app_config.invalidate_cache()
    yield
    app_config.invalidate_cache()


@pytest.mark.asyncio
async def test_load_config_merges_overrides_and_skips_bad_rows():
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [
        {"key": "rag.top_k", "value": json.dumps(8)},
        {"key": "unknown.key", "value": "1"},  # 已废弃 key 忽略
        {"key": "llm.enable_search", "value": "not-json"},  # 脏数据回退默认
    ]
    with patch("app.app_config.get_pool", return_value=mock_pool):
        config = await load_config()
    assert config["rag.top_k"] == 8
    assert config["llm.enable_search"] is True
    assert config["llm.model"] == DEFAULTS["llm.model"]
    assert "unknown.key" not in config


@pytest.mark.asyncio
async def test_load_config_hits_cache_within_ttl():
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = []
    with patch("app.app_config.get_pool", return_value=mock_pool):
        await load_config()
        await load_config()
    assert mock_pool.fetch.await_count == 1  # 第二次命中缓存，不再查库


@pytest.mark.asyncio
async def test_save_config_deletes_row_equal_to_default():
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = []
    with patch("app.app_config.get_pool", return_value=mock_pool):
        await save_config({"rag.top_k": DEFAULTS["rag.top_k"]})
    mock_pool.execute.assert_awaited_once()
    assert mock_pool.execute.await_args.args[0].startswith("DELETE")


@pytest.mark.asyncio
async def test_save_config_upserts_changed_values():
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = []
    with patch("app.app_config.get_pool", return_value=mock_pool):
        await save_config({"rag.top_k": 8, "llm.enable_search": False})
    assert mock_pool.execute.await_count == 2  # 两个非默认值各 upsert 一次
    stored = [call.args[2] for call in mock_pool.execute.await_args_list]
    assert json.dumps(8) in stored
    assert json.dumps(False) in stored


@pytest.mark.asyncio
async def test_save_config_rejects_rag_prompt_without_placeholder():
    with pytest.raises(ValueError, match="占位符"):
        await save_config({"prompt.rag_system": "没有占位符的提示词"})


@pytest.mark.asyncio
async def test_save_config_rejects_unknown_key_and_bad_range():
    with pytest.raises(ValueError, match="未知配置项"):
        await save_config({"foo.bar": 1})
    with pytest.raises(ValueError, match="top_k"):
        await save_config({"rag.top_k": 999})
    with pytest.raises(ValueError, match="空"):
        await save_config({})


@pytest.mark.asyncio
async def test_save_config_returns_saved_values_after_write():
    # save 后缓存失效并重新查库，返回值应包含新值
    mock_pool = AsyncMock()
    mock_pool.fetch.return_value = [{"key": "rag.top_k", "value": json.dumps(8)}]
    with patch("app.app_config.get_pool", return_value=mock_pool):
        result = await save_config({"rag.top_k": 8})
    assert result["rag.top_k"] == 8
