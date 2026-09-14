"use client";

import { useState, useRef } from "react";
import { useSWRConfig } from "swr";
import { DOCUMENTS_KEY } from "@/hooks/use-documents";

// 拖拽上传区：上传成功后通过全局 mutate 刷新文档列表
export default function UploadZone() {
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const { mutate } = useSWRConfig();

  async function uploadFile(file: File) {
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await fetch("/api/python/documents", { method: "POST", body: formData });
      mutate(DOCUMENTS_KEY);
    } finally {
      setUploading(false);
    }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  }

  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
      className={`relative mb-8 rounded-2xl border-2 border-dashed p-10 text-center transition-all ${
        dragOver
          ? "border-violet-400 bg-violet-50/50"
          : "border-gray-200 bg-white hover:border-gray-300"
      }`}
    >
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gray-50">
        <svg className="h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
        </svg>
      </div>
      <p className="text-sm text-gray-600">
        {uploading ? "上传处理中..." : "拖拽文件到此处，或"}
        {!uploading && (
          <label className="ml-1 cursor-pointer font-medium text-violet-600 hover:text-violet-500">
            点击选择
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.md,.markdown"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) uploadFile(file);
                e.target.value = "";
              }}
            />
          </label>
        )}
      </p>
      <p className="mt-2 text-xs text-gray-400">支持 PDF、Markdown 格式</p>
    </div>
  );
}
