"""文档处理恢复机制测试：幂等清理 / 批间心跳 fence / 判死 / 重试门禁（mock 数据层）。"""
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.documents import process_document, reprocess_document, sweep_stale


def _mock_pool():
    return AsyncMock()


@pytest.mark.asyncio
async def test_sweep_stale_returns_killed_count():
    mock_pool = _mock_pool()
    mock_pool.execute.return_value = "UPDATE 2"
    with patch("app.documents.get_pool", return_value=mock_pool):
        assert await sweep_stale() == 2
    args = mock_pool.execute.call_args.args
    assert "lastProgressAt" in args[0]
    assert "processing" in args


@pytest.mark.asyncio
async def test_sweep_stale_zero_when_no_stale():
    mock_pool = _mock_pool()
    mock_pool.execute.return_value = "UPDATE 0"
    with patch("app.documents.get_pool", return_value=mock_pool):
        assert await sweep_stale() == 0


@pytest.mark.asyncio
async def test_process_document_cleans_old_chunks_and_finalizes_ready():
    mock_pool = _mock_pool()
    # fetchrow：第 1 次读处理权代数，第 2 次为批间心跳（未失权）
    mock_pool.fetchrow.side_effect = [{"retryCount": 7}, {"id": "doc-1"}]
    embed_mock = AsyncMock(return_value=[[0.1, 0.2]])
    with patch("app.documents.get_pool", return_value=mock_pool), patch(
        "app.documents.embed_texts", new=embed_mock
    ):
        await process_document("doc-1", "hello world")

    calls = mock_pool.execute.call_args_list
    # 幂等前置：先清旧分块
    assert "DELETE" in calls[0].args[0]
    # 定稿条件写：ready + 携带持有代数（fence）且限定 processing
    finalize = calls[-1].args
    assert "ready" in finalize
    assert finalize[3] == 7
    assert finalize[4] == "processing"


@pytest.mark.asyncio
async def test_process_document_heartbeat_per_batch():
    # 批大小降为 1：每个 chunk 一批，验证每批后都有心跳刷新
    # 每段超过 CHUNK_TARGET(800)，保证切成 3 个独立 chunk（短段落会被贪心合并）
    mock_pool = _mock_pool()
    mock_pool.fetchrow.side_effect = [{"retryCount": 0}] + [{"id": "doc-1"}] * 3
    embed_mock = AsyncMock(side_effect=lambda batch: [[0.0]] * len(batch))
    with patch("app.documents.get_pool", return_value=mock_pool), patch(
        "app.documents.embed_texts", new=embed_mock
    ), patch("app.documents.EMBEDDING_BATCH_SIZE", 1):
        para = "甲" * 850
        await process_document("doc-1", f"{para}\n\n{'乙' * 850}\n\n{'丙' * 850}")
    assert mock_pool.fetchrow.await_count == 4  # 1 次读代数 + 3 次心跳
    assert embed_mock.await_count == 3


@pytest.mark.asyncio
async def test_process_document_aborts_when_fenced():
    # 心跳失权（被重试/删除）→ 主动中止：不插分块、不定稿
    mock_pool = _mock_pool()
    mock_pool.fetchrow.side_effect = [{"retryCount": 0}, None]
    embed_mock = AsyncMock(return_value=[[0.1, 0.2]])
    with patch("app.documents.get_pool", return_value=mock_pool), patch(
        "app.documents.embed_texts", new=embed_mock
    ):
        await process_document("doc-1", "hello world")

    calls = mock_pool.execute.call_args_list
    assert len(calls) == 1  # 仅幂等清理，无分块插入与状态写入
    assert "DELETE" in calls[0].args[0]


@pytest.mark.asyncio
async def test_process_document_failure_sets_last_error():
    mock_pool = _mock_pool()
    mock_pool.fetchrow.side_effect = [{"retryCount": 0}]
    embed_mock = AsyncMock(side_effect=RuntimeError("embedding 接口超时"))
    with patch("app.documents.get_pool", return_value=mock_pool), patch(
        "app.documents.embed_texts", new=embed_mock
    ):
        await process_document("doc-1", "hello world")

    finalize = mock_pool.execute.call_args_list[-1].args
    assert "error" in finalize
    assert "embedding 接口超时" in str(finalize)


@pytest.mark.asyncio
async def test_process_document_skips_when_deleted():
    # 文档已被删除：不做任何写入
    mock_pool = _mock_pool()
    mock_pool.fetchrow.return_value = None
    with patch("app.documents.get_pool", return_value=mock_pool):
        await process_document("doc-1", "hello world")
    mock_pool.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_reprocess_ok_returns_content():
    mock_pool = _mock_pool()
    mock_pool.fetchrow.return_value = {"content": "正文内容"}
    with patch("app.documents.get_pool", return_value=mock_pool):
        assert await reprocess_document("doc-1") == "正文内容"


@pytest.mark.asyncio
async def test_reprocess_404_when_missing():
    mock_pool = _mock_pool()
    mock_pool.fetchrow.side_effect = [None, None]
    with patch("app.documents.get_pool", return_value=mock_pool):
        with pytest.raises(HTTPException) as exc:
            await reprocess_document("doc-1")
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_reprocess_409_when_not_error_state():
    # 条件写未命中（状态非 error），但文档存在
    mock_pool = _mock_pool()
    mock_pool.fetchrow.side_effect = [None, {"id": "doc-1"}]
    with patch("app.documents.get_pool", return_value=mock_pool):
        with pytest.raises(HTTPException) as exc:
            await reprocess_document("doc-1")
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_reprocess_empty_content_fallback_error():
    # 历史数据无原文：回退为 error 并 409，避免卡在 processing
    mock_pool = _mock_pool()
    mock_pool.fetchrow.return_value = {"content": "   "}
    with patch("app.documents.get_pool", return_value=mock_pool):
        with pytest.raises(HTTPException) as exc:
            await reprocess_document("doc-1")
    assert exc.value.status_code == 409
    assert "error" in mock_pool.execute.call_args.args
