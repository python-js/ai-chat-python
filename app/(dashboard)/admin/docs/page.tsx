import { fetchBackend } from "@/lib/backend";
import type { Doc } from "@/hooks/use-documents";
import DocsClient from "./docs-client";

// SSR 聚合：服务端 fetch 文档列表（cookie 转发，与 config/chat 页一致）；
// 后端不可用时降级为 undefined（非空数组），由客户端 SWR 按原逻辑挂载拉取并重试
export default async function DocsPage() {
  const initialDocs = (await fetchBackend<Doc[]>("/api/documents")) ?? undefined;
  return <DocsClient initialDocs={initialDocs} />;
}
