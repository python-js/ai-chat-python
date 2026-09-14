import { headers } from "next/headers";
import { env } from "@/lib/env";

/**
 * SSR 服务端聚合（BFF 模式）：fetch Python 后端。
 * - 转发浏览器请求的 cookie（Python 侧 JWE 鉴权依赖）
 * - 降级策略：Python 未启动 / 非 2xx 时返回 null 并打告警日志，页面渲染空数据而非 500
 */
export async function fetchBackend<T>(path: string): Promise<T | null> {
  try {
    const cookie = (await headers()).get("cookie");
    const res = await fetch(`${env.BACKEND_URL}${path}`, {
      headers: cookie ? { cookie } : {},
      cache: "no-store",
    });
    if (!res.ok) {
      console.warn(`[backend] GET ${path} 返回 ${res.status}`);
      return null;
    }
    return (await res.json()) as T;
  } catch (err) {
    console.warn("[backend] fetch 失败（Python 后端未启动？）:", err);
    return null;
  }
}
