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
        raise HTTPException(status_code=404, detail=f"任务 {task_id} 不存在")

    return {
        "task_id": task_id,
        "status": status.get("status", "unknown"),
        "progress": status.get("meta", {}).get("progress", 0),
        "message": status.get("meta", {}).get("message"),
        "result": status.get("meta", {}).get("result"),
        "error": status.get("meta", {}).get("error")
    }
