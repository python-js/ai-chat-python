"""聊天 SSE 流式编排：对齐 chat.service.ts 流程。

SSE 事件格式（自定义协议，前端 sse-transport 消费）：
    data: {"type":"start"}
    data: {"type":"reasoning_delta","text":"..."}
    data: {"type":"delta","text":"..."}
    data: {"type":"card","data":{...}}     ← 工具查询结果（结构化卡片，可多次）
    data: {"type":"done","text":"完整回答"}
失败时输出 data: {"type":"error","message":"..."}
"""
import asyncio
import json
import logging

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from .app_config import load_config
from .conversations import (
    get_conversation_meta,
    list_context_messages,
    save_message,
    touch_conversation,
)
from .llm import stream_chat
from .mysql import is_enabled as mysql_enabled
from .prompts import CONTEXT_PLACEHOLDER
from .rag import search_similar
from .tools import TOOLS, execute_tool

logger = logging.getLogger(__name__)

# 聊天模式：rag=知识库问答，chat=自由闲聊（默认，可联网搜索）
CHAT_MODES = ("rag", "chat")

# 前置检查结论（见 scripts/precheck.py）：当前模型默认输出 reasoning_content，无需 enable_thinking
ENABLE_THINKING: bool | None = None

# Agent 循环最大 LLM 调用次数（最小 Agent：最多 1 次工具执行 + 1 次总结收尾）。
# 最后一轮强制 tool_choice=none，确保「查到数据必有回答」；后续调大即可支持多步工具组合
MAX_STEPS = 2


def extract_text(message: dict) -> str:
    """从 UIMessage 的 parts 中提取纯文本（过滤 reasoning 等其它 part）。"""
    parts = message.get("parts")
    if isinstance(parts, list):
        return "".join(p.get("text", "") for p in parts if p.get("type") == "text")
    # 兼容纯文本 content 形态
    content = message.get("content")
    return content if isinstance(content, str) else ""


def to_model_messages(messages: list[dict]) -> list[dict]:
    """UIMessage → 百炼 messages（只保留 text，role 限 user/assistant）。"""
    result: list[dict] = []
    for m in messages:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        text = extract_text(m)
        if text:
            result.append({"role": role, "content": text})
    return result


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def trim_by_budget(model_messages: list[dict], max_chars: int) -> list[dict]:
    """输入预算裁剪：总字符超限时从最早消息丢弃（至少保留最后一条）。"""
    total = sum(len(m["content"]) for m in model_messages)
    while total > max_chars and len(model_messages) > 1:
        total -= len(model_messages.pop(0)["content"])
    return model_messages


def _friendly_error(e: Exception) -> str:
    """错误 → 用户可见文案：上下文超限（百炼 400）转友好提示，其余保留原始信息。"""
    response = getattr(e, "response", None)
    body = getattr(response, "text", "") or ""
    if getattr(response, "status_code", None) == 400 and "input length" in body.lower():
        return "当前会话上下文过长，建议压缩上下文或开启新会话"
    return str(e)


async def _save_partial(chat_id: str | None, full_text: str, cards: list[dict]) -> None:
    """客户端中断（停止/断开）时的尽力落库：保存已生成文本与卡片。

    shield 保护落库任务不被二次取消；Serverless 环境实例冻结窗口窄，需回归验证。
    """
    if not chat_id or not (full_text or cards):
        return
    try:
        await asyncio.shield(save_message(chat_id, "assistant", full_text, card_data=cards or None))
    except Exception:
        logger.warning("中断落库失败（已生成内容未保存）", exc_info=True)


async def stream_chat_sse(
    *,
    user_id: str,
    chat_id: str | None,
    messages: list[dict],
    mode: str,
) -> StreamingResponse:
    """校验 → 持久化用户消息 → RAG 检索/自由对话 → Agent 循环流式生成 → 持久化 AI 回复。

    chat 模式且 MySQL 已配置时注册订单工具：循环 = LLM（流式）→ 工具执行 → card 事件 → 再 LLM，
    最多 MAX_STEPS 轮；无工具调用时第一轮即结束（对普通问法零额外开销）。
    """
    if not messages:
        raise HTTPException(status_code=400, detail="消息为空")
    query_text = extract_text(messages[-1])
    if not query_text:
        raise HTTPException(status_code=400, detail="消息内容为空")

    # 持久化会话与用户消息（touch_conversation 内含归属校验 403）
    if chat_id:
        await touch_conversation(chat_id, user_id, query_text)
        await save_message(chat_id, "user", query_text)

    is_chat_mode = mode == "chat"
    config = await load_config()
    if is_chat_mode:
        # 闲聊模式：跳过 RAG 检索，放开 prompt，联网搜索由系统配置开关控制
        system = config["prompt.chat_system"]
        enable_search = config["llm.enable_search"]
    else:
        # 知识库模式：RAG 检索并组装上下文（空知识库走兜底文案）
        chunks = await search_similar(query_text)
        context = "\n\n---\n\n".join(chunks) if chunks else config["chat.empty_context_text"]
        # replace 用回调形式，避免检索内容中的 $ 特殊序列被当作替换模式解释
        system = config["prompt.rag_system"].replace(CONTEXT_PLACEHOLDER, lambda _m: context)
        enable_search = False

    # 订单工具仅在 chat 模式且 MySQL 配置齐全时注册；rag 模式与未配置时链路与原先完全一致
    tools = TOOLS if (is_chat_mode and mysql_enabled()) else None

    # 上下文以 DB 为权威来源（支持压缩点过滤）；无会话 id 时回退前端消息
    if chat_id:
        meta = await get_conversation_meta(chat_id) or {}
        model_messages = await list_context_messages(chat_id, meta.get("summaryUpToId"))
        if meta.get("summary"):
            # 压缩摘要拼接进 system，替代被压缩的历史消息
            system = f"{system}\n\n【历史对话摘要】\n{meta['summary']}"
    else:
        model_messages = to_model_messages(messages)
    # 输入预算裁剪：超过 llm.context_max_chars 时从最早消息静默丢弃
    model_messages = trim_by_budget(model_messages, config["llm.context_max_chars"])

    async def event_stream():
        # 提前初始化：取消/异常分支需访问已生成内容
        cards: list[dict] = []
        full_text = ""
        try:
            yield _sse({"type": "start"})

            for step in range(MAX_STEPS):
                is_last = step == MAX_STEPS - 1
                # 最后一轮强制文本输出（tool_choice=none），避免「查到数据却无回答」
                response = await stream_chat(
                    model_messages,
                    system=system,
                    model=config["llm.model"],
                    enable_search=enable_search,
                    enable_thinking=ENABLE_THINKING,
                    temperature=config["llm.temperature"],
                    max_tokens=config["llm.max_tokens"],
                    tools=tools,
                    tool_choice="none" if (tools and is_last) else None,
                )
                # 本轮流解析：tool_calls 按 index 拼装分片；content/reasoning 实时转发
                #（流式期间无法预知本轮是否调工具，实测模型调工具前 content 为空，直接转发无损体验）
                tool_calls: dict[int, dict] = {}
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
                            # 空 choices chunk（心跳/元数据），跳过，否则索引越界
                            continue
                        delta = choices[0].get("delta", {})
                        reasoning = delta.get("reasoning_content")
                        if reasoning:
                            yield _sse({"type": "reasoning_delta", "text": reasoning})
                        content = delta.get("content")
                        if content:
                            full_text += content
                            yield _sse({"type": "delta", "text": content})
                        for tc in delta.get("tool_calls") or []:
                            slot = tool_calls.setdefault(
                                tc.get("index", 0), {"id": "", "name": "", "arguments": ""}
                            )
                            if tc.get("id"):
                                slot["id"] += tc["id"]
                            fn = tc.get("function") or {}
                            if fn.get("name"):
                                slot["name"] += fn["name"]
                            if fn.get("arguments"):
                                slot["arguments"] += fn["arguments"]
                finally:
                    await response.aclose()

                if not tool_calls:
                    break  # 无工具调用（或工具未启用）：本轮内容即最终回答

                # 执行工具（预定义只读 SQL）→ 卡片推前端 → 结果拼回对话，进入下一轮总结
                assistant_tool_calls = []
                tool_messages = []
                for _idx, slot in sorted(tool_calls.items()):
                    result = await execute_tool(slot["name"], slot["arguments"])
                    if result.get("card"):
                        cards.append(result["card"])
                        yield _sse({"type": "card", "data": result["card"]})
                    # 失败/未找到的结果同样喂回模型，由模型向用户说明（链路不中断）
                    tool_content = json.dumps(
                        result.get("card") or {"message": result.get("message") or "查询无结果"},
                        ensure_ascii=False,
                    )
                    assistant_tool_calls.append(
                        {
                            "id": slot["id"],
                            "type": "function",
                            "function": {"name": slot["name"], "arguments": slot["arguments"]},
                        }
                    )
                    tool_messages.append(
                        {"role": "tool", "tool_call_id": slot["id"], "content": tool_content}
                    )
                model_messages.append(
                    {"role": "assistant", "content": "", "tool_calls": assistant_tool_calls}
                )
                model_messages.extend(tool_messages)

            # 仅最终文本与卡片落库，推理过程不持久化（与现状一致）
            if chat_id and (full_text or cards):
                await save_message(chat_id, "assistant", full_text, card_data=cards or None)
            yield _sse({"type": "done", "text": full_text})
        except asyncio.CancelledError:
            # 客户端中断（用户点停止/连接断开）：尽力保存已生成部分，再继续抛出取消
            await _save_partial(chat_id, full_text, cards)
            raise
        except Exception as e:
            logger.exception("聊天流式处理失败")
            yield _sse({"type": "error", "message": _friendly_error(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
