"use client";

import { useState } from "react";
import { Button } from "@/components/ui";

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled: boolean;
  mode: "rag" | "chat";
  onModeChange: (mode: "rag" | "chat") => void;
}

// 输入区：自管输入内容与回车发送，提交时向上抛出文本
// 左下角为知识库/闲聊模式切换
export default function ChatInput({ onSend, disabled, mode, onModeChange }: ChatInputProps) {
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSend(input);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  return (
    <div className="border-t border-gray-100 bg-white/80 px-6 py-4 backdrop-blur-sm">
      <form onSubmit={handleSubmit} className="mx-auto max-w-[1024px]">
        <div className="flex items-end gap-3 rounded-2xl border border-gray-200 bg-white px-4 py-3 shadow-sm transition-shadow focus-within:border-violet-300 focus-within:shadow-md focus-within:shadow-violet-100/50">
          <div className="flex-1">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题，Enter 发送..."
              rows={3}
              className="max-h-32 w-full resize-none bg-transparent text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none"
            />
            <div className="mt-1.5 flex gap-1">
              {(["rag", "chat"] as const).map((m) => (
                <button
                  key={m}
                  type="button"
                  onClick={() => onModeChange(m)}
                  className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${
                    mode === m
                      ? "bg-violet-600 text-white"
                      : "bg-gray-100 text-gray-500 hover:bg-gray-200"
                  }`}
                >
                  {m === "rag" ? "知识库" : "闲聊"}
                </button>
              ))}
            </div>
          </div>
          <Button
            type="submit"
            size="icon"
            disabled={disabled || !input.trim()}
            className="h-8 w-8 shrink-0 rounded-xl bg-gradient-to-r from-violet-600 to-blue-600 shadow-sm hover:from-violet-500 hover:to-blue-500 disabled:opacity-40"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18" />
            </svg>
          </Button>
        </div>
      </form>
    </div>
  );
}
