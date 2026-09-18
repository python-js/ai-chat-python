"""Agent 订单工具层：预定义 SQL 模板 + 参数校验 + 行→卡片映射。

安全边界（行业共识，缺一不可）：
- SQL 模板写死在代码里，LLM 只能填参数（JSON），绝不透传 LLM 生成的 SQL
- 参数化占位符（%s），杜绝拼接注入
- 仅 SELECT；.env 建议使用只读账号

对接真实业务表时只需改：_ORDERS_TABLE 与 _COLUMNS（列名同构时）或 _row_to_order 映射。
"""
import asyncio
import json
import logging
import re

import aiomysql

from .mysql import get_pool

logger = logging.getLogger(__name__)

# 单次工具执行超时（秒）：防数据源网络问题挂起整条 SSE 流
TOOL_TIMEOUT = 10

# 按客户查询的返回上限：防止卡片爆炸
CUSTOMER_ORDER_LIMIT = 5

# 数据表与列（demo 最小表；对接真实表改这里的表名/列名，或改 _row_to_order 映射）
_ORDERS_TABLE = "demo_orders"
_COLUMNS = (
    "order_id, status, customer_name, customer_phone, product_name, "
    "quantity, amount, tracking_no, created_at, shipped_at"
)

# 参数化 SQL 模板（LIMIT 为代码常量拼接，非用户输入）
_SQL_BY_ID = f"SELECT {_COLUMNS} FROM {_ORDERS_TABLE} WHERE order_id = %s LIMIT 1"
_SQL_BY_PHONE = (
    f"SELECT {_COLUMNS} FROM {_ORDERS_TABLE} WHERE customer_phone = %s "
    f"ORDER BY created_at DESC LIMIT {CUSTOMER_ORDER_LIMIT}"
)
_SQL_BY_NAME = (
    f"SELECT {_COLUMNS} FROM {_ORDERS_TABLE} WHERE customer_name = %s "
    f"ORDER BY created_at DESC LIMIT {CUSTOMER_ORDER_LIMIT}"
)

# 手机号：11 位数字（宽松校验，避免误拒真实数据）
_PHONE_RE = re.compile(r"^\d{11}$")

# 百炼 OpenAI 兼容 tools 定义：LLM 只看到这里（描述质量直接影响选对工具的概率）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order_by_id",
            "description": "根据订单号精确查询单个订单的详细信息（状态、商品、金额、物流单号等）。当用户提供了明确的订单号时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "订单号，例如 ORD20260901001"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_orders_by_customer",
            "description": "根据客户手机号或姓名查询该客户最近的订单列表（最多 5 条）。当用户想了解某位客户的订单、但没有提供具体订单号时使用。phone 与 name 二选一，优先使用手机号。",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string", "description": "客户手机号（11 位数字）"},
                    "name": {"type": "string", "description": "客户姓名"},
                },
            },
        },
    },
]


def _row_to_order(row: dict) -> dict:
    """数据库行 → 卡片条目（前端契约字段 camelCase）。"""
    return {
        "orderId": row["order_id"],
        "status": row["status"],
        "customerName": row["customer_name"],
        "customerPhone": row["customer_phone"],
        "productName": row["product_name"],
        "quantity": row["quantity"],
        "amount": float(row["amount"]),
        "trackingNo": row["tracking_no"],
        "createdAt": row["created_at"].strftime("%Y-%m-%d %H:%M"),
        "shippedAt": row["shipped_at"].strftime("%Y-%m-%d %H:%M") if row["shipped_at"] else None,
    }


async def _fetch(sql: str, param: str) -> list[dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql, (param,))
            return list(await cur.fetchall())


async def _query_order_by_id(args: dict) -> dict:
    order_id = args.get("order_id")
    if not isinstance(order_id, str) or not order_id.strip():
        return {"ok": False, "message": "缺少订单号参数，请向用户确认订单号后重试"}
    order_id = order_id.strip()[:64]
    rows = await _fetch(_SQL_BY_ID, order_id)
    if not rows:
        return {"ok": True, "card": None, "message": f"未找到订单号 {order_id} 对应的订单，请与用户核对订单号是否正确"}
    card = {"kind": "orders", "orders": [_row_to_order(rows[0])]}
    return {"ok": True, "card": card, "message": None}


async def _query_orders_by_customer(args: dict) -> dict:
    phone = args.get("phone")
    name = args.get("name")
    phone = phone.strip() if isinstance(phone, str) else ""
    name = name.strip() if isinstance(name, str) else ""
    if phone:
        if not _PHONE_RE.match(phone):
            return {"ok": False, "message": "手机号格式不正确（应为 11 位数字），请与用户核对"}
        rows = await _fetch(_SQL_BY_PHONE, phone)
        label = phone
    elif name:
        rows = await _fetch(_SQL_BY_NAME, name[:50])
        label = name
    else:
        return {"ok": False, "message": "缺少客户手机号或姓名参数，请向用户询问"}
    if not rows:
        return {"ok": True, "card": None, "message": f"未找到客户 {label} 的订单，请与用户核对信息是否正确"}
    card = {"kind": "orders", "orders": [_row_to_order(r) for r in rows]}
    return {"ok": True, "card": card, "message": None}


async def _dispatch(name: str, args: dict) -> dict:
    if name == "query_order_by_id":
        return await _query_order_by_id(args)
    if name == "query_orders_by_customer":
        return await _query_orders_by_customer(args)
    return {"ok": False, "message": f"未知工具：{name}"}


async def execute_tool(name: str, arguments: str) -> dict:
    """工具执行入口：解析参数 → 分发 → 超时保护。

    返回 {"ok": True, "card": dict | None, "message": str | None}
    或 {"ok": False, "message": 错误描述}。
    失败不抛异常——错误信息作为 tool 结果喂回模型，由模型告知用户（链路不崩）。
    """
    try:
        args = json.loads(arguments) if arguments else {}
    except json.JSONDecodeError:
        return {"ok": False, "message": "工具参数不是合法 JSON"}
    if not isinstance(args, dict):
        return {"ok": False, "message": "工具参数格式错误"}
    try:
        return await asyncio.wait_for(_dispatch(name, args), timeout=TOOL_TIMEOUT)
    except asyncio.TimeoutError:
        logger.warning("工具执行超时: %s", name)
        return {"ok": False, "message": "订单查询超时，请稍后重试"}
    except Exception:
        logger.exception("工具执行失败: %s", name)
        return {"ok": False, "message": "订单查询失败（数据源异常），请稍后重试"}
