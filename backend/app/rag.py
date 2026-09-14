"""RAG 检索：embedding + pgvector 相似度检索，SQL 与 retriever.ts 对齐。"""
from .app_config import load_config
from .db import get_pool
from .llm import embed_texts


async def search_similar(query: str) -> list[str]:
    """返回相关知识块内容；低于阈值/空知识库时返回空列表（调用方走兑底文案）。"""
    config = await load_config()
    [embedding] = await embed_texts([query])
    vector_str = "[" + ",".join(str(x) for x in embedding) + "]"
    pool = await get_pool()
    rows = await pool.fetch(
        'SELECT content FROM "DocumentChunk" '
        "WHERE embedding <=> $1::vector < $3 "
        "ORDER BY embedding <=> $1::vector LIMIT $2",
        vector_str,
        config["rag.top_k"],
        config["rag.distance_threshold"],
    )
    return [row["content"] for row in rows]
