"""初始化 demo_orders 最小订单表 + 样例数据（幂等，可重复运行）。

同时充当 MySQL 连通性验证脚本：建表 → 插样例 → 走工具层公开入口查一单，
一次跑完即验证「连接 → 表结构 → 工具执行 → 卡片映射」全链路。

运行：cd backend && .venv\\Scripts\\python.exe -m scripts.init_demo_orders
（需先在项目根 .env 填好 MYSQL_HOST / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE）
"""
import asyncio
import json

from app.config import settings

DDL = """
CREATE TABLE IF NOT EXISTS demo_orders (
    order_id       VARCHAR(32)   PRIMARY KEY COMMENT '订单号',
    status         VARCHAR(20)   NOT NULL    COMMENT '状态：待付款/已付款/已发货/已签收/已取消',
    customer_name  VARCHAR(50)   NOT NULL    COMMENT '客户姓名',
    customer_phone VARCHAR(20)   NOT NULL    COMMENT '客户手机号',
    product_name   VARCHAR(100)  NOT NULL    COMMENT '商品名',
    quantity       INT           NOT NULL DEFAULT 1 COMMENT '数量',
    amount         DECIMAL(10,2) NOT NULL    COMMENT '金额',
    tracking_no    VARCHAR(50)   NULL        COMMENT '物流单号（未发货为空）',
    created_at     DATETIME      NOT NULL    COMMENT '下单时间',
    shipped_at     DATETIME      NULL        COMMENT '发货时间',
    KEY idx_customer_phone (customer_phone),
    KEY idx_customer_name (customer_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='最小订单演示表'
"""

INSERT_SQL = (
    "INSERT IGNORE INTO demo_orders "
    "(order_id, status, customer_name, customer_phone, product_name, quantity, amount, tracking_no, created_at, shipped_at) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)

# 样例覆盖：同一客户多单（张三 2 单 / 李四 2 单）、多种状态、含未发货无物流单号
ROWS = [
    ("ORD20260901001", "已发货", "张三", "13800001111", "无线机械键盘", 1, 399.00, "SF1234567890", "2026-09-01 10:23:00", "2026-09-02 09:00:00"),
    ("ORD20260901002", "已签收", "张三", "13800001111", "人体工学鼠标", 2, 258.00, "SF1234567891", "2026-09-01 15:40:00", "2026-09-02 14:20:00"),
    ("ORD20260905003", "待付款", "李四", "13900002222", "27寸 4K 显示器", 1, 1899.00, None, "2026-09-05 08:12:00", None),
    ("ORD20260910004", "已付款", "王五", "13700003333", "USB-C 扩展坞", 1, 499.00, None, "2026-09-10 19:05:00", None),
    ("ORD20260912005", "已取消", "李四", "13900002222", "蓝牙音箱", 1, 299.00, None, "2026-09-12 11:30:00", None),
]


async def main() -> None:
    print(f"目标: {settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database} (user={settings.mysql_user})")

    from app.mysql import close_pool, get_pool, is_enabled

    if not is_enabled():
        print("[未启用] 请在项目根 .env 填好 MYSQL_HOST / MYSQL_USER / MYSQL_DATABASE（密码 MYSQL_PASSWORD）后重跑")
        return

    try:
        pool = await get_pool()
    except Exception as e:  # noqa: BLE001 —— 连通性验证脚本，任何连接失败都要打印
        print(f"[连接失败] {e!r}")
        return

    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(DDL)
            inserted = await cur.executemany(INSERT_SQL, ROWS)
            await cur.execute("SELECT COUNT(*) FROM demo_orders")
            (count,) = await cur.fetchone()
    print(f"[建表+样例] 本次新增 {inserted} 行（已存在则跳过），当前共 {count} 行")

    # 走工具层公开入口验证全链路（连接池 → SQL → 行→卡片映射）
    from app.tools import execute_tool

    result = await execute_tool("query_order_by_id", '{"order_id": "ORD20260901001"}')
    print("[工具链路验证] execute_tool(query_order_by_id) 返回:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    await close_pool()
    print("\n结论: ", end="")
    print("连通与工具链路正常，可继续端到端联调" if result.get("ok") else "连通正常但工具返回异常，请检查上方输出")


if __name__ == "__main__":
    asyncio.run(main())
