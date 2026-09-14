import { z } from "zod";

// 服务端环境变量集中校验：关键配置缺失时启动即失败，避免运行到一半才报错
// 注意：本模块仅供服务端代码（lib / server / app/api）导入，不可进入客户端 bundle
const envSchema = z.object({
  DATABASE_URL: z.string().min(1, "DATABASE_URL 不能为空"),
  DASHSCOPE_API_KEY: z.string().min(1, "DASHSCOPE_API_KEY 不能为空"),
  DASHSCOPE_BASE_URL: z
    .string()
    .default("https://dashscope.aliyuncs.com/compatible-mode/v1"),
  LLM_MODEL: z.string().default("qwen-plus"),
  EMBEDDING_MODEL: z.string().default("text-embedding-v3"),
  AUTH_SECRET: z.string().min(1, "AUTH_SECRET 不能为空"),
  // Python 后端地址：SSR 服务端 fetch 使用（rewrites 目标在 next.config.ts 中读取）
  BACKEND_URL: z.string().default("http://localhost:8000"),
});

const parsed = envSchema.safeParse(process.env);

if (!parsed.success) {
  console.error("❌ 环境变量校验失败:", parsed.error.issues);
  throw new Error("环境变量校验失败，请检查 .env 配置");
}

export const env = parsed.data;
