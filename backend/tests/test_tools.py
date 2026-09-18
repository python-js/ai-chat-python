"""订单工具层测试：参数校验、错误兜底、行→卡片映射（mock 数据层，不连真实 MySQL）。"""
from datetime import datetime
from decimal import Decimal
from unittest.mock import patch

import pytest

from app import tools
from app.tools import TOOLS, _row_to_order, execute_tool


def _row(**overrides) -> dict:
    row = {
        "order_id": "ORD1",
        "status": "已发货",
        "customer_name": "张三",
        "customer_phone": "13800001111",
        "product_name": "键盘",
        "quantity": 1,
        "amount": Decimal("399.00"),
        "tracking_no": "SF1",
        "created_at": datetime(2026, 9, 1, 10, 23),
        "shipped_at": datetime(2026, 9, 2, 9, 0),
    }
    row.update(overrides)
    return row


def test_tools_schema_shape():
    """工具定义为百炼/OpenAI 兼容格式，名称与参数齐全。"""
    assert len(TOOLS) == 2
    names = set()
    for t in TOOLS:
        assert t["type"] == "function"
        fn = t["function"]
        assert fn["name"] and fn["description"]
        assert fn["parameters"]["type"] == "object"
        names.add(fn["name"])
    assert names == {"query_order_by_id", "query_orders_by_customer"}


def test_row_to_order_mapping():
    card = _row_to_order(_row())
    assert card["orderId"] == "ORD1"
    assert card["amount"] == 399.0
    assert card["createdAt"] == "2026-09-01 10:23"
    assert card["shippedAt"] == "2026-09-02 09:00"
    assert _row_to_order(_row(shipped_at=None, tracking_no=None))["shippedAt"] is None


async def test_execute_tool_invalid_json():
    result = await execute_tool("query_order_by_id", "not-json")
    assert result["ok"] is False


async def test_execute_tool_unknown_name():
    result = await execute_tool("drop_table", "{}")
    assert result["ok"] is False


async def test_execute_tool_missing_order_id():
    result = await execute_tool("query_order_by_id", "{}")
    assert result["ok"] is False
    assert "订单号" in result["message"]


async def test_execute_tool_customer_requires_phone_or_name():
    result = await execute_tool("query_orders_by_customer", "{}")
    assert result["ok"] is False


async def test_execute_tool_invalid_phone_rejected_before_query():
    """非法手机号在查询前被拒，不触达数据层。"""

    async def should_not_call(sql, param):
        raise AssertionError("不应触达数据层")

    with patch("app.tools._fetch", new=should_not_call):
        result = await execute_tool("query_orders_by_customer", '{"phone": "123"}')
    assert result["ok"] is False
    assert "手机号" in result["message"]


async def test_query_order_by_id_success():
    async def fake_fetch(sql, param):
        assert param == "ORD1"  # order_id 已 strip
        return [_row()]

    with patch("app.tools._fetch", new=fake_fetch):
        result = await execute_tool("query_order_by_id", '{"order_id": " ORD1 "}')
    assert result["ok"] is True
    assert result["card"]["kind"] == "orders"
    assert result["card"]["orders"][0]["orderId"] == "ORD1"


async def test_query_order_by_id_not_found():
    async def fake_fetch(sql, param):
        return []

    with patch("app.tools._fetch", new=fake_fetch):
        result = await execute_tool("query_order_by_id", '{"order_id": "NOPE"}')
    assert result["ok"] is True
    assert result["card"] is None
    assert "未找到" in result["message"]


async def test_query_orders_by_customer_lists_multiple():
    async def fake_fetch(sql, param):
        return [_row(), _row(order_id="ORD2")]

    with patch("app.tools._fetch", new=fake_fetch):
        result = await execute_tool("query_orders_by_customer", '{"phone": "13800001111"}')
    assert result["ok"] is True
    assert [o["orderId"] for o in result["card"]["orders"]] == ["ORD1", "ORD2"]


async def test_query_orders_by_customer_phone_priority_over_name():
    captured = {}

    async def fake_fetch(sql, param):
        captured["param"] = param
        return []

    with patch("app.tools._fetch", new=fake_fetch):
        await execute_tool("query_orders_by_customer", '{"phone": "13800001111", "name": "张三"}')
    assert captured["param"] == "13800001111"


async def test_query_orders_by_customer_name_only():
    captured = {}

    async def fake_fetch(sql, param):
        captured["param"] = param
        return [_row()]

    with patch("app.tools._fetch", new=fake_fetch):
        result = await execute_tool("query_orders_by_customer", '{"name": "张三"}')
    assert captured["param"] == "张三"
    assert result["ok"] is True


async def test_execute_tool_db_error_degraded():
    """数据层异常 → 返回失败信息而非抛异常（链路不中断）。"""

    async def fake_fetch(sql, param):
        raise RuntimeError("db down")

    with patch("app.tools._fetch", new=fake_fetch):
        result = await execute_tool("query_order_by_id", '{"order_id": "ORD1"}')
    assert result["ok"] is False
    assert "失败" in result["message"]


@pytest.mark.asyncio
async def test_execute_tool_timeout_degraded(monkeypatch):
    """执行超时 → 返回超时信息而非挂起链路。"""
    monkeypatch.setattr(tools, "TOOL_TIMEOUT", 0.01)

    async def slow_dispatch(name, args):
        import asyncio as _asyncio

        await _asyncio.sleep(0.5)
        return {"ok": True, "card": None, "message": None}

    monkeypatch.setattr(tools, "_dispatch", slow_dispatch)
    result = await execute_tool("query_order_by_id", '{"order_id": "ORD1"}')
    assert result["ok"] is False
    assert "超时" in result["message"]
