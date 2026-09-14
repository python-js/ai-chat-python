"""前置检查（规划文档实施步骤 1）：
1. 实测 EMBEDDING_MODEL 输出维度是否 = 1024（schema 中 DocumentChunk.embedding 固定 vector(1024)）
2. 实测 LLM_MODEL 是否默认输出 reasoning_content（决定是否需 enable_thinking）
"""
import asyncio
import json

from app.config import settings
from app.llm import _client, stream_chat


async def check_embedding_dim() -> int:
    resp = await _client().post(
        "/embeddings", json={"model": settings.embedding_model, "input": ["测试"]}
    )
    resp.raise_for_status()
    embedding = resp.json()["data"][0]["embedding"]
    print(f"[embedding] 模型 {settings.embedding_model} 输出维度 = {len(embedding)}")
    return len(embedding)


async def check_reasoning() -> bool:
    response = await stream_chat(
        [{"role": "user", "content": "请回答：1+1=？"}],
        system="你是一个乐于助人的 AI 助手。",
        enable_search=False,
    )
    full_text = ""
    reasoning_seen = False
    async for line in response.aiter_lines():
        if not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if data == "[DONE]":
            break
        chunk = json.loads(data)
        # 部分行可能无 choices（如 usage/error），先打印原始结构便于排障
        if not chunk.get("choices"):
            print(f"[chat] 无 choices 的行: {json.dumps(chunk, ensure_ascii=False)[:200]}")
            continue
        delta = chunk["choices"][0].get("delta", {})
        if delta.get("reasoning_content"):
            reasoning_seen = True
        if delta.get("content"):
            full_text += delta["content"]
    print(f"[chat] 模型 {settings.llm_model} 默认输出 reasoning_content: {reasoning_seen}")
    print(f"[chat] 回答前 100 字: {full_text[:100]}")
    return reasoning_seen


async def main() -> None:
    dim = await check_embedding_dim()
    reasoning = await check_reasoning()
    print()
    print(f"结论: embedding 维度 = {dim}{'（符合 vector(1024)）' if dim == 1024 else '（与 schema 不符，需调整）'}")
    print(
        f"结论: reasoning_content 默认输出 = {'是（无需 enable_thinking）' if reasoning else '否（需 enable_thinking: true）'}"
    )


if __name__ == "__main__":
    asyncio.run(main())
