// /api/python/* → Python 后端流式代理
// 说明：next.config 的 rewrites 在 dev 下会缓冲 SSE 流，故改为 route handler 透传响应流
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

async function proxy(
  request: Request,
  { params }: { params: Promise<{ path: string[] }> },
) {
  const { path } = await params;
  const search = new URL(request.url).search;
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/api/${path.join("/")}${search}`, {
      method: request.method,
      headers: {
        cookie: request.headers.get("cookie") ?? "",
        "content-type": request.headers.get("content-type") ?? "",
      },
      body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      // 客户端断开时同步中止上游生成，避免孤儿任务
      signal: request.signal,
    });
  } catch (err) {
    // 上游不可用（Python 未启动/重启中）：返回 502 并携带原因，避免裸 500 空响应
    console.warn(`[bff] ${request.method} /api/${path.join("/")} 代理失败（Python 后端不可用？）:`, err);
    return new Response(JSON.stringify({ detail: "后端服务不可用" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: { "content-type": upstream.headers.get("content-type") ?? "application/json" },
  });
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE };
