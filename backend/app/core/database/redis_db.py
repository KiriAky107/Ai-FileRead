"""
Redis 数据库连接管理模块

提供缓存和任务队列功能
"""
import json
import logging
from datetime import timedelta
from typing import Any, Optional

import redis.asyncio as redis

from app.config import settings

logger = logging.getLogger(__name__)


class RedisDB:
    """Redis 数据库管理类"""

    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connected = False

    async def connect(self):
        """建立 Redis 连接"""
        try:
            self.client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            # 验证连接
            await self.client.ping()
            self._connected = True
            logger.info(f"Redis 连接成功: {settings.REDIS_URL}")
        except Exception as e:
            logger.error(f"Redis 连接失败: {e}")
            raise

    async def close(self):
        """关闭 Redis 连接"""
        if self.client:
            await self.client.close()
            self._connected = False
            logger.info("Redis 连接已关闭")

    @property
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected

    # ==================== 基础操作 ====================

    async def get(self, key: str) -> Optional[str]:
        """获取值"""
        return await self.client.get(key)

    async def set(
        self,
        key: str,
        value: str,
        expire: Optional[int] = None,
    ) -> bool:
        """
        设置值

        Args:
            key: 键
            value: 值
            expire: 过期时间(秒)

        Returns:
            是否成功
        """
        return await self.client.set(key, value, ex=expire)

    async def delete(self, key: str) -> int:
        """删除键"""
        return await self.client.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        return await self.client.exists(key) > 0

    # ==================== JSON 操作 ====================

    async def set_json(
        self,
        key: str,
        data: Dict[str, Any],
        expire: Optional[int] = None,
    ) -> bool:
        """
        设置 JSON 数据

        Args:
            key: 键
            data: 数据字典
            expire: 过期时间(秒)

        Returns:
            是否成功
        """
        json_str = json.dumps(data, ensure_ascii=False, default=str)
        return await self.set(key, json_str, expire)

    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取 JSON 数据

        Args:
            key: 键

        Returns:
            数据字典，不存在返回 None
        """
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    # ==================== 任务状态管理 ====================

    async def set_task_status(
        self,
        task_id: str,
        status: str,
        meta: Optional[Dict[str, Any]] = None,
        expire: int = 86400,  # 默认24小时过期
    ) -> bool:
        """
        设置任务状态

        Args:
            task_id: 任务ID
            status: 状态 (pending/processing/success/failure)
            meta: 附加信息
            expire: 过期时间(秒)

        Returns:
            是否成功
        """
        key = f"task:{task_id}"
        data = {
            "status": status,
            "meta": meta or {},
        }
        return await self.set_json(key, data, expire)

    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态

        Args:
            task_id: 任务ID

        Returns:
            状态信息
        """
        key = f"task:{task_id}"
        return await self.get_json(key)

    async def update_task_progress(
        self,
        task_id: str,
        progress: int,
        message: Optional[str] = None,
    ) -> bool:
        """
        更新任务进度

        Args:
            task_id: 任务ID
            progress: 进度值 (0-100)
            message: 进度消息

        Returns:
            是否成功
        """
        data = await self.get_task_status(task_id)
        if data:
            data["meta"]["progress"] = progress
            if message:
                data["meta"]["message"] = message
            key = f"task:{task_id}"
            return await self.set_json(key, data, expire=86400)
        return False

    # ==================== 缓存操作 ====================

    async def cache_document(
        self,
        doc_id: str,
        data: Dict[str, Any],
        expire: int = 3600,  # 默认1小时
    ) -> bool:
        """
        缓存文档数据

        Args:
            doc_id: 文档ID
            data: 文档数据
            expire: 过期时间(秒)

        Returns:
            是否成功
        """
        key = f"doc:{doc_id}"
        return await self.set_json(key, data, expire)

    async def get_cached_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的文档

        Args:
            doc_id: 文档ID

        Returns:
            文档数据
        """
        key = f"doc:{doc_id}"
        return await self.get_json(key)

    # ==================== 分布式锁 ====================

    async def acquire_lock(
        self,
        lock_name: str,
        expire: int = 30,
    ) -> bool:
        """
        获取分布式锁

        Args:
            lock_name: 锁名称
            expire: 过期时间(秒)

        Returns:
            是否获取成功
        """
        key = f"lock:{lock_name}"
        # 使用 SET NX EX 原子操作
        result = await self.client.set(key, "1", nx=True, ex=expire)
        return result is not None

    async def release_lock(self, lock_name: str) -> bool:
        """
        释放分布式锁

        Args:
            lock_name: 锁名称

        Returns:
            是否释放成功
        """
        key = f"lock:{lock_name}"
        result = await self.client.delete(key)
        return result > 0

    # ==================== 计数器 ====================

    async def incr(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        return await self.client.incrby(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        """递减计数器"""
        return await self.client.decrby(key, amount)

    # ==================== 过期时间管理 ====================

    async def expire(self, key: str, seconds: int) -> bool:
        """设置键的过期时间"""
        return await self.client.expire(key, seconds)

    async def ttl(self, key: str) -> int:
        """获取键的剩余生存时间"""
        return await self.client.ttl(key)


# ==================== 全局单例 ====================

redis_db = RedisDB()
