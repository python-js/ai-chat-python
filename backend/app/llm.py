"""百炼 DashScope（OpenAI 兼容模式）调用：chat 流式 / embeddings。

额外参数（enable_search / enable_thinking）直接放入请求体，
与 TS 侧 providerOptions 机制一致。
"""
import httpx

from .config import settings

# DashScope embedding API 单次请求上限 20 条（对齐 embedder.ts BATCH_SIZE）
EMBEDDING_BATCH_SIZE = 20

_http_client: httpx.AsyncClient | None = None


def _client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=settings.dashscope_base_url,
            headers={"Authorization": f"Bearer {settings.dashscope_api_key}"},
            timeout=httpx.Timeout(300, connect=10),
        )
    return _http_client


async def stream_chat(
    messages: list[dict],
    *,
    system: str,
    enable_search: bool = False,
    enable_thinking: bool | None = None,
) -> httpx.Response:
    """发起流式 chat/completions 请求，返回未读完的流式响应（调用方迭代后需 aclose）。

    必须用 send(stream=True)：普通 post() 会把整个响应体下载完才返回，
    导致 SSE 被整体缓冲、前端一次性收到全部内容。
    """
    body: dict = {
        "model": settings.llm_model,
        "messages": [{"role": "system", "content": system}, *messages],
        "stream": True,
    }
    if enable_search:
        body["enable_search"] = True
    if enable_thinking is not None:
        body["enable_thinking"] = enable_thinking
    client = _client()
    request = client.build_request("POST", "/chat/completions", json=body)
    response = await client.send(request, stream=True)
    try:
        response.raise_for_status()
    except Exception:
        await response.aclose()
        raise
    return response


async def embed_texts(values: list[str]) -> list[list[float]]:
    """分批生成 embedding 向量（对齐 embedder.ts 分批语义）。"""
    results: list[list[float]] = []
    for i in range(0, len(values), EMBEDDING_BATCH_SIZE):
        resp = await _client().post(
            "/embeddings",
            json={"model": settings.embedding_model, "input": values[i : i + EMBEDDING_BATCH_SIZE]},
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(item["embedding"] for item in data["data"])
    return results
