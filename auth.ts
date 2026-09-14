import NextAuth from "next-auth";
import Credentials from "next-auth/providers/credentials";
import bcrypt from "bcryptjs";
import { prisma } from "@/lib/prisma";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Credentials({
      credentials: {
        email: { label: "邮箱", type: "email" },
        password: { label: "密码", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        const user = await prisma.user.findUnique({
          where: { email: credentials.email as string },
        });
        if (!user) return null;

        //bcrypt.compare("admin123", "$2a$10$N9qo8uLOickgx...")
        //         ↓
        // ① 从密文里提取 salt（盐值存在密文前 29 位里）
        // ② 用这个 salt 对明文 "admin123" 重新加密
        // ③ 把加密结果和数据库密文比对
        // ④ 一致 → true，不一致 → false
        const valid = await bcrypt.compare(
          credentials.password as string,
          user.password
        );
        if (!valid) return null;

        return { id: user.id, name: user.name, email: user.email };
      },
    }),
  ],
  pages: {
    signIn: "/login",
  },
  session: {
    strategy: "jwt",
  },
  callbacks: {
    // JWT 策略下用户 id 存在 token.sub，这里把它挂到 session.user.id 方便业务使用
    session({ session, token }) {
      if (session.user) session.user.id = token.sub as string;
      return session;
    },
  },
});
