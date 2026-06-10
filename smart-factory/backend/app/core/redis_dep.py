"""Redis 连接依赖（可选，不可用时降级）"""
import logging
from dataclasses import dataclass

from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger(__name__)
redis_client: Redis | None = None


async def get_redis() -> Redis | None:
    """获取 Redis 连接，不可用时返回 None"""
    global redis_client
    if redis_client is not None:
        return redis_client
    try:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=2,
        )
        await redis_client.ping()
        logger.info("Redis 连接成功")
        return redis_client
    except Exception:
        logger.warning("Redis 不可用，告警去重等功能将降级运行")
        redis_client = FakeRedis()  # type: ignore
        return redis_client


async def close_redis() -> None:
    global redis_client
    if redis_client and not isinstance(redis_client, FakeRedis):
        await redis_client.close()
    redis_client = None


class FakeRedis:
    """内存实现的 Redis 替代，用于无 Redis 环境"""

    def __init__(self):
        self._store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: int = 0) -> None:
        self._store[key] = value

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def ping(self) -> bool:
        return True
