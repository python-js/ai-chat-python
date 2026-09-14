"use client";

import type { RefObject } from "react";
import type { UIMessage } from "ai";
import { ScrollArea } from "@/components/ui";
import MessageItem from "./message-item";
import TypingIndicator from "./typing-indicator";

interface MessageListProps {
  messages: UIMessage[];
  isLoading: boolean;
  bottomRef: RefObject<HTMLDivElement | null>;
}

// 消息区：空态占位 / 消息流 / 加载动画，并锚定自动滚动到底部
export default function MessageList({ messages, isLoading, bottomRef }: MessageListProps) {
  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="mx-auto max-w-[1024px] px-6 py-8"> 
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center pt-32 text-center">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-violet-100 to-blue-100">
              <svg className="h-8 w-8 text-violet-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456Z" />
              </svg>
            </div>
            <h2 className="text-lg font-medium text-gray-800">有什么可以帮你的？</h2>
            <p className="mt-2 text-sm text-gray-400">基于知识库为你解答问题</p>
          </div>
        )}

        <div className="space-y-6">
          {messages.map((m) => (
            <MessageItem key={m.id} message={m} />
          ))}
        </div>

        {isLoading && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
