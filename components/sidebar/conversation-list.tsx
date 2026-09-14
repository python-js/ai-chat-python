"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useConversations } from "@/hooks/use-conversations";
import type { Conversation } from "@/hooks/use-conversations";

// 历史会话列表：SWR 自动缓存与刷新
// 新会话产生后由 chat-client 全局 mutate CONVERSATIONS_KEY 触发更新，无需自定义事件
// initialConversations：SSR 首屏数据，作为 SWR fallbackData 避免闪空
export default function ConversationList({ initialConversations }: { initialConversations: Conversation[] }) {
  const activeConvId = useSearchParams().get("id");
  const { data: conversations = initialConversations } = useConversations(initialConversations);

  return (
    <div className="flex-1 space-y-0.5 overflow-y-auto px-3 py-1">
      {conversations.map((c) => (
        <Link
          key={c.id}
          href={`/chat?id=${c.id}`}
          title={c.title}
          className={`block truncate rounded-lg px-3 py-2 text-sm transition-colors ${
            activeConvId === c.id
              ? "bg-gray-100 font-medium text-gray-900"
              : "text-gray-600 hover:bg-gray-100 hover:text-gray-900"
          }`}
        >
          {c.title}
        </Link>
      ))}
    </div>
  );
}
