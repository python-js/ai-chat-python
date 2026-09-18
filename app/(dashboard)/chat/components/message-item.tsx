"use client";

import { memo, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { UIMessage } from "ai";
import type { OrderCardData } from "@/types/api";
import AiAvatar from "./ai-avatar";
import OrderCard from "./order-card";

// 从消息 parts 中提取纯文本
function extractText(message: UIMessage): string {
  return (
    message.parts?.filter((p): p is { type: "text"; text: string } => p.type === "text").map((p) => p.text).join("") || ""
  );
}

// 从消息 parts 中提取订单卡片数据（data-order part，Agent 工具查询结果，可多张）
function extractCards(message: UIMessage): OrderCardData[] {
  return (
    message.parts
      ?.filter((p): p is { type: "data-order"; data: OrderCardData } => p.type === "data-order")
      .map((p) => p.data) || []
  );
}

// 从消息 parts 中提取推理过程文本（流式期间实时累积）
function extractReasoning(message: UIMessage): string {
  return (
    message.parts
      ?.filter((p): p is { type: "reasoning"; text: string } => p.type === "reasoning")
      .map((p) => p.text)
      .join("") || ""
  );
}

// 推理过程：默认展开，内容增长时内部滚动条跟随到底部；无推理内容时不渲染
function ReasoningBlock({ text }: { text: string }) {
  const contentRef = useRef<HTMLDivElement>(null);

  // 每次 reasoning delta 到达（text 变化）都滚到底部，流式结束后不再触发
  useEffect(() => {
    const el = contentRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [text]);

  if (!text) return null;
  return (
    <details open className="mb-3 rounded-lg border border-dashed border-gray-200 bg-gray-50/60 px-3 py-2">
      <summary className="cursor-pointer select-none text-xs font-medium text-gray-400 hover:text-gray-500">
        思考过程
      </summary>
      <div ref={contentRef} className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-xs leading-relaxed text-gray-500">
        {text}
      </div>
    </details>
  );
}

// 单条消息：用户右对齐紫色气泡，助手左对齐 Markdown 卡片（含折叠的推理过程）
// memo：流式期间 messages 数组每次更新只替换变化的消息对象引用，
// 历史消息引用稳定可整树跳过，避免每个 delta 全部历史消息重渲染 + markdown 重复解析
function MessageItem({ message }: { message: UIMessage }) {
  const text = extractText(message);
  const reasoning = extractReasoning(message);
  const cards = extractCards(message);
  console.log("MessageItem", message);
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] rounded-2xl rounded-br-md bg-gradient-to-r from-violet-600 to-blue-600 px-4 py-3 text-sm text-white shadow-sm">
          <p className="whitespace-pre-wrap">{text}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <AiAvatar />
      <div className="min-w-0 flex-1 rounded-2xl rounded-tl-md border border-gray-100 bg-white px-5 py-4 shadow-sm">
        <ReasoningBlock text={reasoning} />
        {cards.map((card, i) => (
          <OrderCard key={i} data={card} />
        ))}
        <div className="prose prose-sm max-w-none prose-headings:text-gray-800 prose-p:text-gray-600 prose-p:leading-relaxed prose-pre:bg-gray-900 prose-pre:text-gray-100 prose-code:text-violet-600 prose-code:before:content-none prose-code:after:content-none prose-a:text-blue-600 prose-strong:text-gray-800">
          <ReactMarkdown>{text}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

export default memo(MessageItem);
