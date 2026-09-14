// SWR 通用 fetcher：非 2xx 响应抛错，交由 SWR 的 error 状态处理
export async function fetcher<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`请求失败: ${res.status}`);
  }
  return res.json();
}
