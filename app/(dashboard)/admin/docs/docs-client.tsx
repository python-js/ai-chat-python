import { fetchBackend } from "@/lib/backend";
import { ScrollArea } from "@/components/ui";
import type { Doc } from "@/hooks/use-documents";
import UploadZone from "./components/upload-zone";
import DocumentList from "./components/document-list";
import { Suspense } from "react";
import Loading from "@/components/loading";


// 容器：组合上传区 + 文档列表，不含业务细节；列表数据在 Suspense 边界内独立拉取
// （await 置于边界内的 async 子组件：挂起被内层边界捕获，标题与上传区不被阻塞，骨架真实生效）
export default function DocsClient() {
  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-gray-900">知识库管理</h1>
          <p className="mt-1 text-sm text-gray-400">上传 PDF 或 Markdown 文档，AI 将基于这些内容回答问题</p>
        </div>

        <UploadZone />
        <Suspense fallback={<Loading />}>
          <DocsListContent />   {/* 数据就绪后替换骨架屏 */}
        </Suspense>
      </div>
    </ScrollArea>
  );
}

// initialDocs 为 SSR 预取数据（undefined = 降级，交回 SWR 客户端拉取）
async function DocsListContent() {
  const initialDocs = (await fetchBackend<Doc[]>("/api/documents")) ?? undefined;
  return <DocumentList initialDocs={initialDocs} />;
}
