"use client";

import { useState, useRef, useEffect } from "react";
import { useChat } from "@ai-sdk/react";
import type { UIMessage } from "ai";
import { useSWRConfig } from "swr";
import { CONVERSATIONS_KEY } from "@/hooks/use-conversations";
import { sseTransport } from "./sse-transport";
import MessageList from "./components/message-list";
import ChatInput from "./components/chat-input";

interface ChatClientProps {
  chatId?: string;
  initialMessages?: UIMessage[];
  // 以下两项由 chat/page.tsx SSR 注入（系统配置，失败时回退内置默认值）
  defaultMode?: "rag" | "chat";
  welcomeText?: string;
}

// 容器：编排 useChat 状态 + 子件渲染，不含 UI 细节
export default function ChatClient({
  chatId,
  initialMessages,
  defaultMode = "chat",
  welcomeText = "有什么可以帮你的？",
}: ChatClientProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const notifiedRef = useRef(false);
  const { mutate } = useSWRConfig();
  // 新会话（无 chatId）时本地生成稳定 id，作为会话主键发给服务端
  const [stableId] = useState(() => chatId ?? crypto.randomUUID());
  // 对话模式：rag=知识库问答，chat=自由闲聊（默认模式由系统配置注入）
  const [mode, setMode] = useState<"rag" | "chat">(defaultMode);
  const [compressLoading, setCompressLoading] = useState(false);
  const [compressFailed, setCompressFailed] = useState(false);

  const { messages, sendMessage, status, stop } = useChat({
    id: stableId,
    // AI SDK v7 的 ChatInit 用 messages 字段接收初始消息（旧版 initialMessages 已废弃，会被静默忽略）
    messages: initialMessages,
    // 自定义 SSE transport：/api/python/chat（Next rewrites 代理到 FastAPI），
    // 支持 delta → text part、reasoning_delta → reasoning part 两类流式事件
    transport: sseTransport,
  });

  const isLoading = status === "submitted" || status === "streaming";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // 新会话产生第一条消息后，全局 mutate 刷新侧边栏会话列表（只触发一次）
  useEffect(() => {
    if (!chatId && messages.length > 0 && !notifiedRef.current) {
      notifiedRef.current = true;
      mutate(CONVERSATIONS_KEY);
    }
  }, [messages.length, chatId, mutate]);

  function handleSend(text: string) {
    // body.mode 随请求发送，服务端据此分流（rag=知识库 / chat=闲聊）
    sendMessage({ text }, { body: { mode } });
  }

  // 手动压缩上下文：仅按钮反馈（成功无提示；失败文案短暂变红后恢复）
  async function handleCompress() {
    setCompressLoading(true);
    setCompressFailed(false);
    try {
      const res = await fetch(`/api/python/conversations/${stableId}/compress`, { method: "POST" });
      if (!res.ok) throw new Error(`压缩失败: HTTP ${res.status}`);
    } catch (err) {
      console.warn("[chat] 压缩上下文失败：", err);
      setCompressFailed(true);
      setTimeout(() => setCompressFailed(false), 2500);
    } finally {
      setCompressLoading(false);
    }
  }

  return (
    <>
      <MessageList
        messages={messages}
        isLoading={isLoading}
        bottomRef={bottomRef}
        welcomeText={welcomeText}
      />
      {/* 压缩禁用条件与后端 KEEP_RECENT=4 对齐：消息不足或会话进行中不可压缩 */}
      <ChatInput
        onSend={handleSend}
        onStop={stop}
        disabled={isLoading}
        mode={mode}
        onModeChange={setMode}
        onCompress={handleCompress}
        compressDisabled={compressLoading || messages.length <= 4 || status !== "ready"}
        compressLoading={compressLoading}
        compressFailed={compressFailed}
      />
    </>
  );
}
