import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";

// 前端按线上格式消费：日期字段经 JSON 序列化后为字符串
export interface Doc {
  id: string;
  filename: string;
  fileType: string;
  status: string;
  lastError?: string | null;
  createdAt: string;
}

// 共享缓存 key：上传成功后通过全局 mutate 此 key 触发文档列表刷新
// 浏览器直连 /api/python/* 经 rewrites 代理到 Python 后端
export const DOCUMENTS_KEY = "/api/python/documents";

export function useDocuments(initialDocs?: Doc[]) {
  return useSWR<Doc[]>(DOCUMENTS_KEY, fetcher, {
    // SSR 预取数据：命中时首屏直出且不重复挂载请求；降级（undefined）时按原逻辑挂载拉取
    fallbackData: initialDocs,
    revalidateOnMount: initialDocs === undefined,
    // 存在未终态文档时 3s 轮询，全部就绪后自动停止
    refreshInterval: (data) =>
      data?.some((d) => d.status === "pending" || d.status === "processing") ? 3000 : 0,
  });
}
