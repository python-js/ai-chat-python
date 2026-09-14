import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

// 前端按线上格式消费：日期字段经 JSON 序列化后为字符串
export interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
}

// 共享缓存 key：chat-client 新会话产生后通过全局 mutate 此 key 触发侧边栏刷新
// 浏览器直连 /api/python/* 经 rewrites 代理到 Python 后端
export const CONVERSATIONS_KEY = "/api/python/conversations";

export function useConversations(fallbackData?: Conversation[]) {
  // fallbackData：SSR 注入的首屏数据（layout 服务端 fetch Python 获得）
  return useSWR<Conversation[]>(CONVERSATIONS_KEY, fetcher, { fallbackData });
}
