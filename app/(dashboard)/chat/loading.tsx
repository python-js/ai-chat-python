// 切换会话时 DB 查询期间的过渡态（Next.js 约定：自动包裹 page）
export default function ChatLoading() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:0ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-violet-400 [animation-delay:300ms]" />
      </div>
    </div>
  );
}
