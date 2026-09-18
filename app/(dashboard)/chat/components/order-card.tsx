import type { OrderCardData, OrderCardItem } from "@/types/api";

// 订单状态配色（与 demo_orders 状态枚举对应；未知状态回退灰色）
const STATUS_STYLES: Record<string, string> = {
  待付款: "bg-amber-50 text-amber-600 border-amber-200",
  已付款: "bg-blue-50 text-blue-600 border-blue-200",
  已发货: "bg-violet-50 text-violet-600 border-violet-200",
  已签收: "bg-green-50 text-green-600 border-green-200",
  已取消: "bg-gray-100 text-gray-500 border-gray-200",
};

const DEFAULT_STATUS_STYLE = "bg-gray-100 text-gray-500 border-gray-200";

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <span className="shrink-0 text-xs text-gray-400">{label}</span>
      <span className="text-xs text-gray-700">{value}</span>
    </div>
  );
}

function OrderRow({ order }: { order: OrderCardItem }) {
  const statusStyle = STATUS_STYLES[order.status] ?? DEFAULT_STATUS_STYLE;
  return (
    <div className="px-4 py-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="font-mono text-sm font-medium text-gray-800">{order.orderId}</span>
        <span className={`inline-flex h-5 items-center rounded-full border px-2 text-xs font-medium ${statusStyle}`}>
          {order.status}
        </span>
      </div>
      <div className="mb-2 text-sm text-gray-700">
        {order.productName}
        {order.quantity > 1 && <span className="text-gray-400"> × {order.quantity}</span>}
        <span className="ml-2 font-medium text-violet-600">¥{order.amount.toFixed(2)}</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1">
        <Field label="客户" value={order.customerName} />
        <Field label="手机号" value={order.customerPhone} />
        <Field label="下单时间" value={order.createdAt} />
        {order.trackingNo && <Field label="物流单号" value={order.trackingNo} />}
      </div>
    </div>
  );
}

// 订单卡片：Agent 工具查询结果的结构化展示（单条订单 → 单卡；多条 → 同卡列表）
export default function OrderCard({ data }: { data: OrderCardData }) {
  // 防御异常数据：kind 不符或无订单时不渲染
  if (data?.kind !== "orders" || !data.orders?.length) return null;
  return (
    <div className="mb-3 overflow-hidden rounded-xl border border-gray-100 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-gray-50 bg-gray-50/70 px-4 py-2">
        <span className="text-xs font-medium text-gray-500">订单查询结果</span>
        <span className="text-xs text-gray-400">共 {data.orders.length} 条</span>
      </div>
      <div className="divide-y divide-gray-50">
        {data.orders.map((order) => (
          <OrderRow key={order.orderId} order={order} />
        ))}
      </div>
    </div>
  );
}
