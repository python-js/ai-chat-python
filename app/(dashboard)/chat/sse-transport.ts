import type { ChatTransport, UIMessage, UIMessageChunk } from "ai";

// 后端 SSE 事件（与 FastAPI chat.py 约定一致）
interface SseEvent {
  type: "start" | "delta" | "reasoning_delta" | "done" | "error";
  text?: string;
  message?: string;
}

/**
 * 自定义 SSE transport：fetch /api/python/chat（Next rewrites 代理到 FastAPI），
 * 把后端 SSE 事件流转换为 AI SDK v7 的 UIMessageChunk 流。
 * delta → text part，reasoning_delta → reasoning part（前端已有折叠渲染，零改动）。
 */
export const sseTransport: ChatTransport<UIMessage> = {
  async sendMessages({ chatId, messages, body, abortSignal }) {
    const response = await fetch("/api/python/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: chatId, messages, ...body }),
      signal: abortSignal,
    });

    if (!response.ok || !response.body) {
      throw new Error(`聊天请求失败: HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();

    return new ReadableStream<UIMessageChunk>({
      async start(controller) {
        const partId = crypto.randomUUID();
        let textStarted = false;
        let reasoningStarted = false;
        let buffer = "";

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            // SSE 按行切分（后端每条事件一行 data: {...}）
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";
            for (const line of lines) {
              const trimmed = line.trim();
              if (!trimmed.startsWith("data:")) continue;
              const event = JSON.parse(trimmed.slice(5).trim()) as SseEvent;
              switch (event.type) {
                case "start":
                  break;
                case "reasoning_delta":
                  if (!reasoningStarted) {
                    reasoningStarted = true;
                    controller.enqueue({ type: "reasoning-start", id: partId });
                  }
                  controller.enqueue({ type: "reasoning-delta", id: partId, delta: event.text ?? "" });
                  break;
                case "delta":
                  if (!textStarted) {
                    textStarted = true;
                    controller.enqueue({ type: "text-start", id: partId });
                  }
                  controller.enqueue({ type: "text-delta", id: partId, delta: event.text ?? "" });
                  break;
                case "done":
                  if (textStarted) controller.enqueue({ type: "text-end", id: partId });
                  if (reasoningStarted) controller.enqueue({ type: "reasoning-end", id: partId });
                  controller.enqueue({ type: "finish", finishReason: "stop" });
                  break;
                case "error":
                  controller.enqueue({ type: "error", errorText: event.message ?? "服务端错误" });
                  break;
              }
            }
          }
        } catch (err) {
          controller.error(err instanceof Error ? err : new Error(String(err)));
          return;
        }
        controller.close();
      },
    });
  },

  // 后端不维护可恢复的流状态，断线重连直接返回 null（SDK 视为无需重连）
  async reconnectToStream() {
    return null;
  },
};
