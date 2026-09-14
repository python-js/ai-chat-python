"""聊天 SSE 流式编排：对齐 chat.service.ts 流程。

SSE 事件格式（自定义协议，前端 sse-transport 消费）：
    data: {"type":"start"}
    data: {"type":"reasoning_delta","text":"..."}
    data: {"type":"delta","text":"..."}
    data: {"type":"done","text":"完整回答"}
失败时输出 data: {"type":"error","message":"..."}
"""
import json
import logging

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from .app_config import load_config
from .conversations import save_message, touch_conversation
from .llm import stream_chat
from .prompts import CONTEXT_PLACEHOLDER
from .rag import search_similar

logger = logging.getLogger(__name__)

# 聊天模式：rag=知识库问答，chat=自由闲聊（默认，可联网搜索）
CHAT_MODES = ("rag", "chat")

# 前置检查结论（见 scripts/precheck.py）：当前模型默认输出 reasoning_content，无需 enable_thinking
ENABLE_THINKING: bool | None = None


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


async def stream_chat_sse(
    *,
    user_id: str,
    chat_id: str | None,
    messages: list[dict],
    mode: str,
) -> StreamingResponse:
    """校验 → 持久化用户消息 → RAG 检索/自由对话 → 流式生成 → 持久化 AI 回复。"""
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

    model_messages = to_model_messages(messages)

    async def event_stream():
        try:
            yield _sse({"type": "start"})
            response = await stream_chat(
                model_messages,
                system=system,
                model=config["llm.model"],
                enable_search=enable_search,
                enable_thinking=ENABLE_THINKING,
                temperature=config["llm.temperature"],
                max_tokens=config["llm.max_tokens"],
            )
            full_text = ""
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
            finally:
                await response.aclose()
            # 仅最终文本落库，推理过程不持久化（与现状一致）
            if chat_id and full_text:
                await save_message(chat_id, "assistant", full_text)
            yield _sse({"type": "done", "text": full_text})
        except Exception as e:
            logger.exception("聊天流式处理失败")
            yield _sse({"type": "error", "message": str(e)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
