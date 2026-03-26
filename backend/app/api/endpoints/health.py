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
    mysql_status = "connected"
    mongodb_status = "connected"
    redis_status = "connected"

    try:
        if mysql_db.async_engine is None:
            mysql_status = "disconnected"
    except Exception:
        mysql_status = "error"

    try:
        if mongodb.client is None:
            mongodb_status = "disconnected"
    except Exception:
        mongodb_status = "error"

    try:
        if not redis_db.is_connected:
            redis_status = "disconnected"
    except Exception:
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
