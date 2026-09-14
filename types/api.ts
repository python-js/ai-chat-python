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
