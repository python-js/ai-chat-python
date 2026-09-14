"use client";

import { ScrollArea } from "@/components/ui";
import UploadZone from "./components/upload-zone";
import DocumentList from "./components/document-list";

// 容器：组合上传区 + 文档列表，不含业务细节
export default function DocsClient() {
  return (
    <ScrollArea className="flex-1">
      <div className="mx-auto max-w-2xl px-6 py-8">
        <div className="mb-8">
          <h1 className="text-xl font-semibold text-gray-900">知识库管理</h1>
          <p className="mt-1 text-sm text-gray-400">上传 PDF 或 Markdown 文档，AI 将基于这些内容回答问题</p>
        </div>

        <UploadZone />
        <DocumentList />
      </div>
    </ScrollArea>
  );
}
