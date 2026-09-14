import { fetchBackend } from "@/lib/backend";
import type { AppConfigDto } from "@/types/api";
import ChatClient from "./chat-client";
import type { UIMessage } from "ai";

// 消息历史（后端返回格式，与 FastAPI conversations 接口一致）
interface MessageDto {
  id: string;
  role: string;
  content: string;
}

export default async function ChatPage({
  searchParams,
}: {
  searchParams: Promise<{ id?: string }>;
}) {
  const { id } = await searchParams;

  // 打开历史会话时，SSR 聚合：服务端 fetch Python 消息历史（cookie 转发，含归属校验 403）
  // 失败或越权时降级为空历史，页面正常渲染
  let initialMessages: UIMessage[] = [];
  if (id) {
    const msgs = await fetchBackend<MessageDto[]>(`/api/conversations/${id}/messages`);
    initialMessages = (msgs ?? []).map((m) => ({
      id: m.id,
      role: m.role as "user" | "assistant",
      parts: [{ type: "text" as const, text: m.content }],
    }));
  }

  // 系统配置注入：默认对话模式与欢迎语（后端不可用时回退内置默认值）
  const config = await fetchBackend<AppConfigDto>("/api/config");
  const defaultMode = config?.values["chat.default_mode"] ?? "chat";
  const welcomeText = config?.values["chat.welcome_text"] ?? "有什么可以帮你的？";

  // key 保证切换会话时组件重挂载，重置 useChat 状态
  return (
    <ChatClient
      key={id ?? "new"}
      chatId={id}
      initialMessages={initialMessages}
      defaultMode={defaultMode}
      welcomeText={welcomeText}
    />
  );
}
