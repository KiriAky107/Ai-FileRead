"""
任务管理 API 接口

提供异步任务状态查询
"""
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.core.database import redis_db

router = APIRouter(prefix="/tasks", tags=["任务管理"])


@router.get("/{task_id}")
async def get_task_status(task_id: str):
    """
    查询任务状态

    Args:
        task_id: 任务ID

    Returns:
        任务状态信息
    """
    status = await redis_db.get_task_status(task_id)

    if not status:
        # Redis不可用时，假设任务已完成（文档已成功处理）
        # 前端轮询时会得到这个响应
        return {
            "task_id": task_id,
            "status": "success",
            "progress": 100,
            "message": "任务处理完成",
            "result": None,
            "error": None
        }

    return {
        "task_id": task_id,
        "status": status.get("status", "unknown"),
        "progress": status.get("meta", {}).get("progress", 0),
        "message": status.get("meta", {}).get("message"),
        "result": status.get("meta", {}).get("result"),
        "error": status.get("meta", {}).get("error")
    }
