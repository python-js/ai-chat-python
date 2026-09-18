import { Suspense } from "react";
import { fetchBackend } from "@/lib/backend";
import type { AppConfigDto, OrderCardData } from "@/types/api";
import ChatClient from "./chat-client";
import ChatLoading from "./loading";
import type { UIMessage } from "ai";

// 消息历史（后端返回格式，与 FastAPI conversations 接口一致）
interface MessageDto {
  id: string;
  role: string;
  content: string;
  cardData?: OrderCardData[] | null; // 历史订单卡片（工具查询结果，落库于 Message.cardData）
}

// 切换会话属于同段 searchParams 导航（React 对已挂载边界保持旧内容，loading.tsx 不生效），
// 用 key 让 Suspense 边界随会话重新挂载 → 切换时立即显示过渡态
// （fallback 复用 loading.tsx 同款：跨段导航时两层边界切换视觉无缝）
export default async function ChatPage({
  searchParams,
}: {
  searchParams: Promise<{ id?: string }>;
}) {
  const { id } = await searchParams;

  return (
    <Suspense key={id ?? "new"} fallback={<ChatLoading />}>
      <ChatContent id={id} />
    </Suspense>
  );
}

// 数据聚合：消息历史 + 系统配置（原 page 主体逻辑）
async function ChatContent({ id }: { id?: string }) {
  // 打开历史会话时，SSR 聚合：服务端 fetch Python 消息历史（cookie 转发，含归属校验 403）
  // 失败或越权时降级为空历史，页面正常渲染
  let initialMessages: UIMessage[] = [];
  if (id) {
    const msgs = await fetchBackend<MessageDto[]>(`/api/conversations/${id}/messages`);
    initialMessages = (msgs ?? []).map((m) => ({
      id: m.id,
      role: m.role as "user" | "assistant",
      // 恢复顺序：卡片 data part 在前、文本 part 在后，与流式渲染顺序一致
      parts: [
        ...(m.cardData ?? []).map((card, i) => ({
          type: "data-order" as const,
          id: `${m.id}-card-${i}`,
          data: card,
        })),
        { type: "text" as const, text: m.content },
      ],
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
