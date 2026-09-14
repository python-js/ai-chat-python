"use client";

import ErrorFallback from "@/components/error-fallback";

// chat 级错误兜底：消息加载失败时独立降级，不影响侧边栏等其他区域
export default function ChatError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorFallback error={error} reset={reset} message="会话加载失败" />;
}
