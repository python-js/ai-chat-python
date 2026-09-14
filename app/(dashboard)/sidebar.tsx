"use client";

import Link from "next/link";
import { signOut } from "next-auth/react";
import { Button } from "@/components/ui";
import ConversationList from "@/components/sidebar/conversation-list";
import NavMenu from "@/components/sidebar/nav-menu";
import type { Conversation } from "@/hooks/use-conversations";

// 容器：组合 Logo + 新对话 + 会话列表 + 导航 + 退出
// initialConversations：SSR 注入的首屏数据（作为 SWR fallbackData，避免闪空）
export default function Sidebar({ initialConversations }: { initialConversations: Conversation[] }) {
  return (
    <aside className="flex w-64 flex-col border-r border-gray-200/80 bg-white">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-blue-600">
          <svg className="h-4.5 w-4.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
          </svg>
        </div>
        <span className="text-[15px] font-semibold text-gray-900">智能客服</span>
      </div>

      {/* 新对话 */}
      <div className="px-3 pb-3">
        <Link href="/chat">
          <Button variant="outline" className="w-full justify-start gap-2 border-dashed text-gray-500 hover:text-gray-900">
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            新对话
          </Button>
        </Link>
      </div>

      {/* 历史会话列表（SWR 驱动，SSR 数据经 fallbackData 注入） */}
      <ConversationList initialConversations={initialConversations} />

      <div className="mx-3 border-t" />

      {/* 导航菜单（配置驱动） */}
      <NavMenu />

      {/* 退出登录 */}
      <div className="border-t px-3 py-3">
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2.5 text-sm text-gray-500 transition-colors hover:bg-red-50 hover:text-red-600"
        >
          <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-6a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 7.5 21h6a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
          </svg>
          退出登录
        </button>
      </div>
    </aside>
  );
}
