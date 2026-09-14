"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import {
  Button,
  Card,
  CardAction,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  ScrollArea,
  Textarea,
} from "@/components/ui";
import type { AppConfigDto, AppConfigValues } from "@/types/api";

// 分组定义：组内 key 列表，供「恢复默认」整组回填
const GROUPS = {
  prompt: ["prompt.rag_system", "prompt.chat_system"],
  llm: ["llm.model", "llm.temperature", "llm.max_tokens", "llm.enable_search"],
  rag: ["rag.distance_threshold", "rag.top_k"],
  chat: [
    "chat.title_max_length",
    "chat.default_mode",
    "chat.welcome_text",
    "chat.empty_context_text",
  ],
} satisfies Record<string, (keyof AppConfigValues)[]>;

// 表单字段壳：标签 + 控件 + 说明
function Field({
  id,
  label,
  hint,
  children,
}: {
  id: string;
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
    </div>
  );
}

// 胶囊按钮组（样式对齐 chat-input 的模式切换）
function Pills({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex gap-1">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => onChange(o.value)}
          className={`rounded-full px-3 py-0.5 text-xs font-medium transition-colors ${
            value === o.value
              ? "bg-violet-600 text-white"
              : "bg-gray-100 text-gray-500 hover:bg-gray-200"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

// 前端轻校验：与后端 app_config._validate 对齐的常见错误（后端仍兜底）
function validate(v: AppConfigValues): string {
  if (!v["prompt.rag_system"].includes("{{context}}"))
    return "知识库提示词必须包含 {{context}} 占位符";
  if (!v["llm.model"].trim()) return "模型名不能为空";
  if (v["llm.temperature"] !== null && !(v["llm.temperature"] >= 0 && v["llm.temperature"] <= 2))
    return "temperature 需要在 0~2 之间（或留空）";
  if (v["llm.max_tokens"] !== null && !(v["llm.max_tokens"] >= 1 && v["llm.max_tokens"] <= 32768))
    return "max_tokens 需要在 1~32768 之间（或留空）";
  if (!(v["rag.distance_threshold"] >= 0 && v["rag.distance_threshold"] <= 2))
    return "距离阈值需要在 0~2 之间";
  if (!(v["rag.top_k"] >= 1 && v["rag.top_k"] <= 20)) return "召回条数需要在 1~20 之间";
  if (!(v["chat.title_max_length"] >= 1 && v["chat.title_max_length"] <= 100))
    return "标题截断长度需要在 1~100 之间";
  if (!v["chat.welcome_text"].trim()) return "欢迎语不能为空";
  if (!v["chat.empty_context_text"].trim()) return "未命中文案不能为空";
  return "";
}

export default function ConfigClient({ initial }: { initial: AppConfigDto | null }) {
  const [values, setValues] = useState<AppConfigValues | null>(initial?.values ?? null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function set<K extends keyof AppConfigValues>(key: K, value: AppConfigValues[K]) {
    setValues((prev) => (prev ? { ...prev, [key]: value } : prev));
    setMessage("");
    setError("");
  }

  // 整组回填默认值（实际写入需点保存）
  function restoreGroup(group: keyof typeof GROUPS) {
    if (!values || !initial) return;
    const next: AppConfigValues = { ...values };
    for (const k of GROUPS[group]) Object.assign(next, { [k]: initial.defaults[k] });
    setValues(next);
    setMessage("");
    setError("");
  }

  async function handleSave() {
    if (!values) return;
    const invalid = validate(values);
    if (invalid) {
      setError(invalid);
      setMessage("");
      return;
    }
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const res = await fetch("/api/python/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(typeof data.detail === "string" ? data.detail : `保存失败：HTTP ${res.status}`);
        return;
      }
      // 用返回值更新（保存后立即生效于本实例，不重新 GET 规避多实例缓存延迟）
      setValues(data.values);
      setMessage("已保存");
    } catch {
      setError("保存失败，请检查网络或后端状态");
    } finally {
      setSaving(false);
    }
  }

  if (!values) {
    return (
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto max-w-2xl px-6 py-8">
          <h1 className="text-xl font-semibold text-gray-900">系统设置</h1>
          <p className="mt-6 text-sm text-gray-400">
            无法加载配置，请确认后端服务已启动后刷新页面。
          </p>
        </div>
      </ScrollArea>
    );
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="mx-auto max-w-2xl space-y-6 px-6 py-8">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">系统设置</h1>
          <p className="mt-1 text-sm text-gray-400">
            保存后约 30 秒内在所有实例生效；改回默认值的项将自动恢复为跟随默认
          </p>
        </div>

        {/* 提示词 */}
        <Card>
          <CardHeader>
            <CardTitle>提示词</CardTitle>
            <CardDescription>系统级指令，对所有用户全局生效</CardDescription>
            <CardAction>
              <Button variant="ghost" size="xs" onClick={() => restoreGroup("prompt")}>
                恢复默认
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field
              id="rag-system"
              label="知识库问答提示词"
              hint="必须保留 {{context}} 占位符，检索到的知识库内容会替换到该位置"
            >
              <Textarea
                id="rag-system"
                rows={8}
                className="font-mono text-xs"
                value={values["prompt.rag_system"]}
                onChange={(e) => set("prompt.rag_system", e.target.value)}
              />
            </Field>
            <Field id="chat-system" label="闲聊提示词">
              <Textarea
                id="chat-system"
                rows={5}
                className="font-mono text-xs"
                value={values["prompt.chat_system"]}
                onChange={(e) => set("prompt.chat_system", e.target.value)}
              />
            </Field>
          </CardContent>
        </Card>

        {/* 生成参数 */}
        <Card>
          <CardHeader>
            <CardTitle>生成参数</CardTitle>
            <CardDescription>模型与采样参数</CardDescription>
            <CardAction>
              <Button variant="ghost" size="xs" onClick={() => restoreGroup("llm")}>
                恢复默认
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-4">
            <Field
              id="llm-model"
              label="模型"
              hint="百炼（DashScope）模型名，如 qwen-plus / qwen-max / qwen-turbo"
            >
              <Input
                id="llm-model"
                value={values["llm.model"]}
                onChange={(e) => set("llm.model", e.target.value)}
              />
            </Field>
            <div className="grid grid-cols-2 gap-4">
              <Field id="llm-temperature" label="温度 temperature" hint="留空 = 不传，走模型默认">
                <Input
                  id="llm-temperature"
                  type="number"
                  min={0}
                  max={2}
                  step={0.1}
                  value={values["llm.temperature"] ?? ""}
                  onChange={(e) =>
                    set("llm.temperature", e.target.value === "" ? null : Number(e.target.value))
                  }
                />
              </Field>
              <Field id="llm-max-tokens" label="最大输出 max_tokens" hint="留空 = 不传，走模型默认">
                <Input
                  id="llm-max-tokens"
                  type="number"
                  min={1}
                  max={32768}
                  step={1}
                  value={values["llm.max_tokens"] ?? ""}
                  onChange={(e) =>
                    set("llm.max_tokens", e.target.value === "" ? null : Number(e.target.value))
                  }
                />
              </Field>
            </div>
            <Field id="llm-enable-search" label="闲聊模式联网搜索">
              <Pills
                options={[
                  { value: "on", label: "开启" },
                  { value: "off", label: "关闭" },
                ]}
                value={values["llm.enable_search"] ? "on" : "off"}
                onChange={(v) => set("llm.enable_search", v === "on")}
              />
            </Field>
          </CardContent>
        </Card>

        {/* RAG 检索 */}
        <Card>
          <CardHeader>
            <CardTitle>RAG 检索</CardTitle>
            <CardDescription>知识库问答的检索范围</CardDescription>
            <CardAction>
              <Button variant="ghost" size="xs" onClick={() => restoreGroup("rag")}>
                恢复默认
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4">
            <Field id="rag-threshold" label="距离阈值" hint="越小越严格，0~2">
              <Input
                id="rag-threshold"
                type="number"
                min={0}
                max={2}
                step={0.05}
                value={values["rag.distance_threshold"]}
                onChange={(e) => set("rag.distance_threshold", Number(e.target.value))}
              />
            </Field>
            <Field id="rag-top-k" label="召回条数 top_k" hint="1~20">
              <Input
                id="rag-top-k"
                type="number"
                min={1}
                max={20}
                step={1}
                value={values["rag.top_k"]}
                onChange={(e) => set("rag.top_k", Number(e.target.value))}
              />
            </Field>
          </CardContent>
        </Card>

        {/* 对话体验 */}
        <Card>
          <CardHeader>
            <CardTitle>对话体验</CardTitle>
            <CardDescription>聊天页默认行为与文案（新打开页面时读取）</CardDescription>
            <CardAction>
              <Button variant="ghost" size="xs" onClick={() => restoreGroup("chat")}>
                恢复默认
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field id="title-max" label="标题截断长度" hint="会话标题取首条提问的字数，1~100">
                <Input
                  id="title-max"
                  type="number"
                  min={1}
                  max={100}
                  step={1}
                  value={values["chat.title_max_length"]}
                  onChange={(e) => set("chat.title_max_length", Number(e.target.value))}
                />
              </Field>
              <Field id="default-mode" label="默认对话模式">
                <Pills
                  options={[
                    { value: "rag", label: "知识库" },
                    { value: "chat", label: "闲聊" },
                  ]}
                  value={values["chat.default_mode"]}
                  onChange={(v) => set("chat.default_mode", v === "rag" ? "rag" : "chat")}
                />
              </Field>
            </div>
            <Field id="welcome-text" label="欢迎语">
              <Input
                id="welcome-text"
                value={values["chat.welcome_text"]}
                onChange={(e) => set("chat.welcome_text", e.target.value)}
              />
            </Field>
            <Field
              id="empty-context"
              label="未命中知识库时的上下文文案"
              hint="检索为空时放入提示词的内容"
            >
              <Input
                id="empty-context"
                value={values["chat.empty_context_text"]}
                onChange={(e) => set("chat.empty_context_text", e.target.value)}
              />
            </Field>
          </CardContent>
        </Card>

        {/* 保存 */}
        <div className="flex items-center gap-3 pb-4">
          <Button onClick={handleSave} disabled={saving}>
            {saving ? "保存中..." : "保存"}
          </Button>
          {message && <span className="text-sm text-green-600">{message}</span>}
          {error && <span className="text-sm text-red-500">{error}</span>}
        </div>
      </div>
    </ScrollArea>
  );
}
