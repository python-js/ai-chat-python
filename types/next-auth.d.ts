import { DefaultSession } from "next-auth";

// 扩展 NextAuth 默认会话类型：JWT 策略下通过 callback 把用户 id 挂到 session.user.id
declare module "next-auth" {
  interface Session {
    user: {
      id: string;
    } & DefaultSession["user"];
  }
}
