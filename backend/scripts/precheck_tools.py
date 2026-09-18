"""工具调用预检：实测当前模型（LLM_MODEL）流式 tool_calls 的真实协议格式。

验证三点（chat.py Agent 循环的解析逻辑与参数取舍依赖此结论）：
1. 流式 tool_calls 分片格式：id/name 是否仅首片出现、arguments 是否逐片拼接
2. enable_search 与 tools 能否并存（chat 模式默认联网搜索，冲突则工具轮需关闭搜索）
3. tool 消息回合格式：百炼兼容模式是否接受 assistant(tool_calls) + role=tool 的拼装，
   以及 tool_choice="none" 是否强制文本输出（循环最后一轮收尾用）

运行：cd backend && .venv\\Scripts\\python.exe -m scripts.precheck_tools
"""
import asyncio
import json

from app.config import settings
from app.llm import stream_chat

# 与 tools.py 中真实 schema 保持同构（仅用于协议验证，字段从简）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_order_by_id",
            "description": "根据订单号精确查询单个订单的详细信息（状态、物流等）",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string", "description": "订单号"}},
                "required": ["order_id"],
            },
        },
    }
]

SYSTEM = "你是订单客服助手。用户询问订单时调用工具查询后再回答。"


async def consume(title: str, messages: list[dict], *, enable_search: bool, tool_choice: str | None) -> None:
    """发一轮流式请求，打印 tool_calls 拼装结果与 finish_reason。"""
    print(f"\n===== {title} =====")
    print(f"参数: enable_search={enable_search} tool_choice={tool_choice}")
    try:
        response = await stream_chat(
            messages,
            system=SYSTEM,
            model=settings.llm_model,
            enable_search=enable_search,
            tools=TOOLS,
            tool_choice=tool_choice,
        )
    except Exception as e:  # noqa: BLE001 —— 预检脚本，任何失败都要打印出来
        print(f"[请求失败] {e!r}")
        return

    calls: dict[int, dict] = {}
    finish_reason: str | None = None
    content = ""
    raw_samples: list[str] = []
    try:
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            choices = chunk.get("choices")
            if not choices:
                # 空 choices 行（错误/心跳）打印出来便于排障
                if len(raw_samples) < 3:
                    raw_samples.append(json.dumps(chunk, ensure_ascii=False)[:300])
                continue
            choice = choices[0]
            finish_reason = choice.get("finish_reason") or finish_reason
            delta = choice.get("delta", {})
            if len(raw_samples) < 3 and (delta.get("tool_calls") or delta.get("content") or delta.get("reasoning_content")):
                raw_samples.append(json.dumps(delta, ensure_ascii=False)[:300])
            if delta.get("content"):
                content += delta["content"]
            for tc in delta.get("tool_calls") or []:
                idx = tc.get("index", 0)
                slot = calls.setdefault(idx, {"id": "", "name": "", "arguments": ""})
                if tc.get("id"):
                    slot["id"] += tc["id"]
                fn = tc.get("function") or {}
                if fn.get("name"):
                    slot["name"] += fn["name"]
                if fn.get("arguments"):
                    slot["arguments"] += fn["arguments"]
    finally:
        await response.aclose()

    print("前 3 个非空 delta 样本:")
    for s in raw_samples:
        print(f"  {s}")
    print(f"finish_reason = {finish_reason}")
    print(f"content 长度 = {len(content)}，前 80 字: {content[:80]!r}")
    if calls:
        for idx, slot in sorted(calls.items()):
            args_valid = True
            try:
                json.loads(slot["arguments"] or "{}")
            except json.JSONDecodeError:
                args_valid = False
            print(f"tool_call[{idx}] id={slot['id']!r} name={slot['name']!r} "
                  f"arguments={slot['arguments']!r} JSON合法={args_valid}")
    else:
        print("tool_calls: 无（模型未调用工具）")


async def main() -> None:
    print(f"模型: {settings.llm_model}")

    # 用例 A：tools + 联网搜索并存（chat 模式默认开的场景）
    await consume(
        "A. tools + enable_search=True（共存性验证）",
        [{"role": "user", "content": "帮我查一下订单 ORD20260901001 的状态"}],
        enable_search=True,
        tool_choice=None,
    )

    # 用例 B：tools + 关闭搜索（对照组，确认 tool_calls 正常路径）
    await consume(
        "B. tools + enable_search=False（tool_calls 标准路径）",
        [{"role": "user", "content": "帮我查一下订单 ORD20260901001 的状态"}],
        enable_search=False,
        tool_choice=None,
    )

    # 用例 C：模拟 Agent 循环第二轮（tool 结果回合 + 强制文本输出）
    await consume(
        "C. tool 回合格式 + tool_choice=none（最后一轮收尾验证）",
        [
            {"role": "user", "content": "帮我查一下订单 ORD20260901001 的状态"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "call_demo_1",
                        "type": "function",
                        "function": {"name": "query_order_by_id", "arguments": '{"order_id": "ORD20260901001"}'},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "call_demo_1",
                "content": json.dumps({"order_id": "ORD20260901001", "status": "已发货", "tracking_no": "SF1234567890"}, ensure_ascii=False),
            },
        ],
        enable_search=False,
        tool_choice="none",
    )


if __name__ == "__main__":
    asyncio.run(main())
