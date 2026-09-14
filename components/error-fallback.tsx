"use client";

interface ErrorFallbackProps {
  error: Error & { digest?: string };
  reset: () => void;
  message?: string;
}

// 通用错误兜底 UI：error.tsx 必须是 client component，共享此组件避免重复
export default function ErrorFallback({ reset, message = "页面加载出现问题" }: ErrorFallbackProps) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-red-50">
        <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
        </svg>
      </div>
      <div>
        <p className="text-sm font-medium text-gray-800">{message}</p>
        <p className="mt-1 text-xs text-gray-400">请稍后重试，问题将持续存在时联系管理员</p>
      </div>
      <button
        onClick={reset}
        className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-700"
      >
        重试
      </button>
    </div>
  );
}
