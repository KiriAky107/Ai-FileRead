"""
健康检查接口
"""
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

from app.core.database import mysql_db, mongodb, redis_db

router = APIRouter(tags=["健康检查"])


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    健康检查接口

    返回各数据库连接状态和应用信息
    """
    # 检查各数据库连接状态
    mysql_status = "unknown"
    mongodb_status = "unknown"
    redis_status = "unknown"

    try:
        if mysql_db.async_engine is None:
            mysql_status = "disconnected"
        else:
            # 实际执行一次查询验证连接
            from sqlalchemy import text
            async with mysql_db.async_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            mysql_status = "connected"
    except Exception as e:
        logger.warning(f"MySQL 健康检查失败: {e}")
        mysql_status = "error"

    try:
        if mongodb.client is None:
            mongodb_status = "disconnected"
        else:
            # 实际 ping 验证
            await mongodb.client.admin.command('ping')
            mongodb_status = "connected"
    except Exception as e:
        logger.warning(f"MongoDB 健康检查失败: {e}")
        mongodb_status = "error"

    try:
        if not redis_db.is_connected or redis_db.client is None:
            redis_status = "disconnected"
        else:
            # 实际执行 ping 验证
            await redis_db.client.ping()
            redis_status = "connected"
    except Exception as e:
        logger.warning(f"Redis 健康检查失败: {e}")
        redis_status = "error"

    return {
        "status": "healthy" if all([
            mysql_status == "connected",
            mongodb_status == "connected",
            redis_status == "connected"
        ]) else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {
            "mysql": mysql_status,
            "mongodb": mongodb_status,
            "redis": redis_status,
        }
    }


@router.get("/health/ready")
async def readiness_check() -> Dict[str, str]:
    """
    就绪检查接口

    用于 Kubernetes/负载均衡器检查服务是否就绪
    """
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    存活检查接口

    用于 Kubernetes/负载均衡器检查服务是否存活
    """
    return {"status": "alive"}
