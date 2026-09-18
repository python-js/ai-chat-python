"""MySQL 只读连接池：Agent 订单工具专用。

host/user/database 三项齐全才启用（is_enabled），缺省时整层禁用、
聊天功能不受影响。池保持小（本地/单用户场景），生命周期挂 main.py lifespan。
"""
import aiomysql

from .config import settings

_pool: aiomysql.Pool | None = None


def is_enabled() -> bool:
    """MySQL 配置是否齐全（齐 = 注册订单工具）。"""
    return bool(settings.mysql_host and settings.mysql_user and settings.mysql_database)


async def get_pool() -> aiomysql.Pool:
    global _pool
    if _pool is None:
        _pool = await aiomysql.create_pool(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            db=settings.mysql_database,
            minsize=1,
            maxsize=3,
            autocommit=True,
            charset="utf8mb4",
            connect_timeout=5,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        await _pool.wait_closed()
        _pool = None
