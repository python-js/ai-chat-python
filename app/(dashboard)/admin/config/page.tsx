import { fetchBackend } from "@/lib/backend";
import type { AppConfigDto } from "@/types/api";
import ConfigClient from "./config-client";

export default async function ConfigPage() {
  // SSR 拉取配置（含默认值，供「恢复默认」使用）；后端未启动时降级为提示态
  const config = await fetchBackend<AppConfigDto>("/api/config");
  return <ConfigClient initial={config} />;
}
