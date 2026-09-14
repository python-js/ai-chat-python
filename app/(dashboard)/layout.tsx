import { auth } from "@/auth";
import { redirect } from "next/navigation";
import DashboardShell from "./dashboard-shell";
import { fetchBackend } from "@/lib/backend";
import type { Conversation } from "@/hooks/use-conversations";

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // 统一鉴权：路由组内所有页面共享，无需各自再写守卫
  const session = await auth();
  if (!session?.user) redirect("/login");

  // SSR 聚合：服务端 fetch Python 会话列表（cookie 转发），失败时降级为空列表
  const conversations = (await fetchBackend<Conversation[]>("/api/conversations")) ?? [];

  // 布局壳为客户端组件（管理手机端抽屉状态），children 作为 RSC 槽位传入
  return (
    <DashboardShell initialConversations={conversations}>
      {children}
    </DashboardShell>
  );
}
