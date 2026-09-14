"use client";

import { Suspense, useState } from "react";
import Sidebar from "./sidebar";
import type { Conversation } from "@/hooks/use-conversations";

// 布局壳：编排「侧边栏 + 手机端顶栏 + 内容区」，管理手机端抽屉开关状态
// 手机端（<768px）：侧边栏默认收起，点汉堡滑出，点遮罩/菜单项关闭；桌面端恒显
export default function DashboardShell({
  initialConversations,
  children,
}: {
  initialConversations: Conversation[];
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden bg-[#f7f8fa]">
      {/* Suspense 包裹：Sidebar 内部使用 useSearchParams 读取当前会话 id */}
      <Suspense fallback={<aside className="hidden w-64 border-r border-gray-200/80 bg-white md:block" />}>
        <Sidebar
          initialConversations={initialConversations}
          open={open}
          onClose={() => setOpen(false)}
        />
      </Suspense>

      {/* 手机端遮罩：点击关闭抽屉（桌面端不渲染） */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setOpen(false)}
        />
      )}

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 手机端顶栏：汉堡按钮打开抽屉（参考 deepseek） */}
        <header className="flex h-12 shrink-0 items-center gap-2 border-b border-gray-200/80 bg-white px-3 md:hidden">
          <button
            type="button"
            aria-label="打开侧边栏"
            onClick={() => setOpen(true)}
            className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-600 transition-colors hover:bg-gray-100"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
            </svg>
          </button>
          <span className="text-sm font-semibold text-gray-900">智能客服</span>
        </header>
        <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
      </div>
    </div>
  );
}
