import { PrismaClient } from "../app/generated/prisma/client";
import { PrismaPg } from "@prisma/adapter-pg";
import bcrypt from "bcryptjs";
import "dotenv/config";

const adapter = new PrismaPg({ connectionString: process.env.DATABASE_URL! });
const prisma = new PrismaClient({ adapter });

async function main() {
  const password = await bcrypt.hash("admin123", 10);
  await prisma.user.upsert({
    where: { email: "admin@company.com" },
    update: {},
    create: {
      name: "管理员",
      email: "admin@company.com",
      password,
    },
  });
  console.log("种子用户已创建: admin@company.com / admin123");
}

main()
  .catch(console.error)
  .finally(() => prisma.$disconnect());
