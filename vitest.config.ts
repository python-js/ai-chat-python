import { defineConfig } from "vitest/config";
import path from "node:path";
import { fileURLToPath } from "node:url";

export default defineConfig({
  resolve: {
    // 与 tsconfig.json 的 paths 保持一致
    alias: {
      "@": path.dirname(fileURLToPath(import.meta.url)),
    },
  },
  test: {
    // 测试环境加载 .env，使 lib/env.ts 校验通过（conversation.service 间接依赖）
    setupFiles: ["./vitest.setup.ts"],
  },
});
