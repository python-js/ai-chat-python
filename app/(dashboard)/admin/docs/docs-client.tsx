"use client";

import { ScrollArea } from "@/components/ui";
import type { Doc } from "@/hooks/use-documents";
import UploadZone from "./components/upload-zone";
import DocumentList from "./components/document-list";

// 容器：组合上传区 + 文档列表，不含业务细节；initialDocs 为 SSR 预取数据（undefined = 降级）
export default function DocsClient({ initialDocs }: { initialDocs?: Doc[] }) {
  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-gray-900">知识库管理</h1>
          <p className="mt-1 text-sm text-gray-400">上传 PDF 或 Markdown 文档，AI 将基于这些内容回答问题</p>
        </div>

        <UploadZone />
        <DocumentList initialDocs={initialDocs} />
      </div>
    </ScrollArea>
  );
}
