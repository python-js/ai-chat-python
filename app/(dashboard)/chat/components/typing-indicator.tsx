"use client";

import AiAvatar from "./ai-avatar";

// 流式生成中的加载动画（三点跳动）
export default function TypingIndicator() {
  return (
    <div className="mt-6 flex gap-3">
      <AiAvatar />
      <div className="rounded-2xl rounded-tl-md border border-gray-100 bg-white px-5 py-4 shadow-sm">
        <div className="flex items-center gap-1.5">
          <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:0ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:150ms]" />
          <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
