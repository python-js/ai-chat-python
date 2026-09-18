import Loading from "@/components/loading";

// 切换会话时 DB 查询期间的过渡态（Next.js 约定：自动包裹 page）
export default function ChatLoading() {
  return <Loading />;
}
