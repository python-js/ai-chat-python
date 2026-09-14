"use client";

import ErrorFallback from "@/components/error-fallback";

// dashboard 级错误兜底：捕获子页面服务端异常（DB 故障等）
export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorFallback error={error} reset={reset} />;
}
