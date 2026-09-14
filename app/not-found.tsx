import Link from "next/link";

// 全局 404：用户访问不存在的路径时展示
export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-[#f7f8fa]">
      <p className="text-4xl font-bold text-gray-200">404</p>
      <p className="text-sm text-gray-500">页面不存在</p>
      <Link
        href="/chat"
        className="rounded-lg bg-gray-900 px-4 py-2 text-sm text-white transition-colors hover:bg-gray-700"
      >
        返回对话
      </Link>
    </div>
  );
}
