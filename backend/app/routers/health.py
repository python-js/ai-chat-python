import asyncio
import socket
import time

from fastapi import APIRouter

router = APIRouter(prefix="/api")

# 临时诊断目标（验证后连同 debug 端点在后续提交中删除）
_DEBUG_HOST = "dashscope.aliyuncs.com"


@router.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok"}


@router.get("/debug/net")
async def debug_net() -> dict:
    """临时诊断端点：域名解析顺序 + 逐地址 TCP 连接计时（验证 Vercel 沙箱 IPv6 出网行为）。"""
    infos = socket.getaddrinfo(_DEBUG_HOST, 443, type=socket.SOCK_STREAM)
    results = []
    seen: set[str] = set()
    for family, _, _, _, addr in infos:
        ip = addr[0]
        if ip in seen:
            continue
        seen.add(ip)
        started = time.monotonic()
        try:
            _, writer = await asyncio.wait_for(asyncio.open_connection(ip, 443), timeout=5)
            writer.close()
            error = None
        except Exception as exc:  # 诊断端点：捕获所有异常并回传
            error = repr(exc)
        results.append(
            {
                "ip": ip,
                "family": family.name,
                "ms": round((time.monotonic() - started) * 1000),
                "error": error,
            }
        )
    return {"marker": "debug-net-v1", "host": _DEBUG_HOST, "addresses": [a[4][0] for a in infos], "tests": results}
