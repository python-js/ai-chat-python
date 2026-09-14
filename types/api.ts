// 前后端共享的 API 数据契约
// 服务端 service 按此返回，前端（阶段 3）按此消费，避免接口字段脱节
// 注意：Date 字段经 JSON 序列化后在浏览器端为字符串

export interface ConversationDto {
  id: string;
  title: string;
  updatedAt: Date;
}

export interface DocumentDto {
  id: string;
  filename: string;
  fileType: string;
  status: string;
  createdAt: Date;
}

// 系统配置（key 命名与 backend/app_config.py 的 DEFAULTS 对齐）
export interface AppConfigValues {
  "prompt.rag_system": string;
  "prompt.chat_system": string;
  "llm.model": string;
  "llm.temperature": number | null;
  "llm.max_tokens": number | null;
  "llm.enable_search": boolean;
  "rag.distance_threshold": number;
  "rag.top_k": number;
  "chat.title_max_length": number;
  "chat.default_mode": "rag" | "chat";
  "chat.welcome_text": string;
  "chat.empty_context_text": string;
}

// GET/PUT /api/config 响应：values=当前生效值，defaults=内置默认值（供「恢复默认」）
export interface AppConfigDto {
  values: AppConfigValues;
  defaults: AppConfigValues;
}
