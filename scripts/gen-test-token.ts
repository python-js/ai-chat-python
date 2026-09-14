// 生成一个 next-auth v5 真实签发的 JWE 会话 token，供 backend pytest 验证解密逻辑
// 用法: pnpm exec tsx scripts/gen-test-token.ts [cookie名] [sub] [maxAge秒]
import { encode } from "next-auth/jwt";
import "dotenv/config";

const cookieName = process.argv[2] ?? "authjs.session-token";
const sub = process.argv[3] ?? "test-user-123";
const maxAge = process.argv[4] ? Number(process.argv[4]) : undefined;

const secret = process.env.AUTH_SECRET;
if (!secret) {
  console.error("缺少 AUTH_SECRET");
  process.exit(1);
}
// 注：process.env 索引返回 string | undefined，前面已判空，此处断言收窄
const secretStr: string = secret;

async function main() {
  const token = await encode({
    token: { sub, name: "测试用户", email: "test@example.com" },
    secret: secretStr,
    salt: cookieName,
    ...(maxAge ? { maxAge } : {}),
  });
  process.stdout.write(token);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
