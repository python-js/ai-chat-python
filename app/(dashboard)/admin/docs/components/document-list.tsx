"use client";

import { useState } from "react";
import { useSWRConfig } from "swr";
import {
    Badge,
    Button,
    Card,
    CardContent,
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui";
import { DOCUMENTS_KEY, useDocuments, type Doc } from "@/hooks/use-documents";

const statusConfig: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  pending: { label: "等待中", variant: "outline" },
  processing: { label: "处理中", variant: "secondary" },
  ready: { label: "就绪", variant: "default" },
  error: { label: "失败", variant: "destructive" },
};

// 文档列表：SWR 驱动，展示已上传文档及处理状态，支持删除
export default function DocumentList() {
  const { data: docs = [] } = useDocuments();
  const { mutate } = useSWRConfig();
  // 删除确认走 Dialog 弹窗（替代原生 confirm/alert），错误提示展示在弹窗内
  const [pendingDoc, setPendingDoc] = useState<Doc | null>(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    if (!pendingDoc) return;
    setError("");
    setDeleting(true);
    try {
      const res = await fetch(`/api/python/documents/${pendingDoc.id}`, { method: "DELETE" });
      if (!res.ok) {
        setError(`删除失败：HTTP ${res.status}`);
        return;
      }
      setPendingDoc(null);
      mutate(DOCUMENTS_KEY);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-medium text-gray-700">已上传文档</h2>
        <span className="text-xs text-gray-400">{docs.length} 份</span>
      </div>

      {docs.length === 0 && (
        <Card className="border-dashed">
          <CardContent className="py-10 text-center text-sm text-gray-400">
            暂无文档，上传后即可使用
          </CardContent>
        </Card>
      )}

      {docs.map((doc) => {
        const cfg = statusConfig[doc.status] || { label: doc.status, variant: "outline" as const };
        return (
          <Card key={doc.id} className="transition-shadow hover:shadow-sm">
            <CardContent className="flex items-center justify-between py-3.5">
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gray-50">
                  {doc.fileType === "pdf" ? (
                    <svg className="h-4.5 w-4.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                    </svg>
                  ) : (
                    <svg className="h-4.5 w-4.5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                    </svg>
                  )}
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-800">{doc.filename}</p>
                  <p className="text-xs text-gray-400">
                    {doc.fileType.toUpperCase()} · {new Date(doc.createdAt).toLocaleString("zh-CN")}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={cfg.variant} className="text-xs">
                  {cfg.label}
                </Badge>
                <button
                  type="button"
                  onClick={() => {
                    setError("");
                    setPendingDoc(doc);
                  }}
                  title="删除文档"
                  className="rounded-md p-1.5 text-gray-300 transition-colors hover:bg-red-50 hover:text-red-500"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                  </svg>
                </button>
              </div>
            </CardContent>
            {doc.status === "processing" && (
              <div className="h-0.5 overflow-hidden rounded-b-lg bg-gray-100">
                <div className="h-full w-1/4 animate-[indeterminate_1.5s_ease-in-out_infinite] bg-blue-400" />
              </div>
            )}
          </Card>
        );
      })}

      {/* 删除确认弹窗：仅控制显隐，确认后走 DELETE 接口并刷新列表 */}
      <Dialog
        open={!!pendingDoc}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDoc(null);
            setError("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除文档</DialogTitle>
            <DialogDescription>
              确定删除「{pendingDoc?.filename}」？其向量数据将一并删除，此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingDoc(null)}>
              取消
            </Button>
            <Button variant="destructive" disabled={deleting} onClick={confirmDelete}>
              {deleting ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
