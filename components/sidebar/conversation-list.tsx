"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useSWRConfig } from "swr";
import {
    Button,
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui";
import { CONVERSATIONS_KEY, useConversations } from "@/hooks/use-conversations";
import type { Conversation } from "@/hooks/use-conversations";

// 历史会话列表：SWR 自动缓存与刷新
// 新会话产生后由 chat-client 全局 mutate CONVERSATIONS_KEY 触发更新，无需自定义事件
// initialConversations：SSR 首屏数据，作为 SWR fallbackData 避免闪空
export default function ConversationList({ initialConversations }: { initialConversations: Conversation[] }) {
  const activeConvId = useSearchParams().get("id");
  const { data: conversations = initialConversations } = useConversations(initialConversations);
  const { mutate } = useSWRConfig();
  const router = useRouter();
  // 删除确认走 Dialog 弹窗（替代原生 confirm），错误提示展示在弹窗内
  const [pendingConv, setPendingConv] = useState<Conversation | null>(null);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState(false);

  async function confirmDelete() {
    if (!pendingConv) return;
    setError("");
    setDeleting(true);
    try {
      const res = await fetch(`/api/python/conversations/${pendingConv.id}`, { method: "DELETE" });
      if (!res.ok) {
        setError(`删除失败：HTTP ${res.status}`);
        return;
      }
      // 删除的是当前打开的会话 → 跳回空白新对话页
      if (pendingConv.id === activeConvId) router.push("/chat");
      setPendingConv(null);
      mutate(CONVERSATIONS_KEY);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="flex-1 space-y-0.5 overflow-y-auto px-3 py-1">
        {conversations.map((c) => (
          <div key={c.id} className="group relative">
            <Link
              href={`/chat?id=${c.id}`}
              title={c.title}
              className={`block truncate rounded-lg py-2 pl-3 pr-9 text-sm transition-colors ${
                activeConvId === c.id
                  ? "bg-gray-100 font-medium text-gray-900"
                  : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
              }`}
            >
              {c.title}
            </Link>

            {/* 「⋯」操作菜单：桌面悬停浮现，手机端常显 */}
            <DropdownMenu>
              <DropdownMenuTrigger
                aria-label="会话操作"
                className="absolute top-1/2 right-1 -translate-y-1/2 rounded-md p-1 text-gray-500 transition-opacity hover:bg-gray-200/70 md:opacity-0 md:group-hover:opacity-100 md:focus-visible:opacity-100 md:data-popup-open:opacity-100"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z" />
                </svg>
              </DropdownMenuTrigger>
              <DropdownMenuContent>
                <DropdownMenuItem
                  className="text-red-600 data-highlighted:bg-red-50 data-highlighted:text-red-600"
                  onClick={() => {
                    setError("");
                    setPendingConv(c);
                  }}
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
                  </svg>
                  删除
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ))}
      </div>

      {/* 删除确认弹窗：仅控制显隐，确认后走 DELETE 接口并刷新列表 */}
      <Dialog
        open={!!pendingConv}
        onOpenChange={(open) => {
          if (!open) {
            setPendingConv(null);
            setError("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除对话</DialogTitle>
            <DialogDescription>
              确定删除「{pendingConv?.title}」？该对话的聊天记录将一并删除，此操作不可恢复。
            </DialogDescription>
          </DialogHeader>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <DialogFooter>
            <Button variant="outline" onClick={() => setPendingConv(null)}>
              取消
            </Button>
            <Button variant="destructive" disabled={deleting} onClick={confirmDelete}>
              {deleting ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
