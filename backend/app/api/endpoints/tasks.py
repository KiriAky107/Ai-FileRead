"""
任务管理 API 接口

提供异步任务状态查询和历史记录
"""
from typing import Optional

from fastapi import APIRouter, HTTPException

from app.core.database import redis_db, mongodb

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
    # 优先从 Redis 获取
    status = await redis_db.get_task_status(task_id)

    if status:
        return {
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("meta", {}).get("progress", 0),
            "message": status.get("meta", {}).get("message"),
            "result": status.get("meta", {}).get("result"),
            "error": status.get("meta", {}).get("error")
        }

    # Redis 不可用时，尝试从 MongoDB 获取
    mongo_task = await mongodb.get_task(task_id)
    if mongo_task:
        return {
            "task_id": mongo_task.get("task_id"),
            "status": mongo_task.get("status", "unknown"),
            "progress": 100 if mongo_task.get("status") == "success" else 0,
            "message": mongo_task.get("message"),
            "result": mongo_task.get("result"),
            "error": mongo_task.get("error")
        }

    # 任务不存在或状态未知
    return {
        "task_id": task_id,
        "status": "unknown",
        "progress": 0,
        "message": "无法获取任务状态（Redis和MongoDB均不可用）",
        "result": None,
        "error": None
    }


@router.get("/")
async def list_tasks(limit: int = 50, skip: int = 0):
    """
    获取任务历史列表

    Args:
        limit: 返回数量限制
        skip: 跳过数量

    Returns:
        任务列表
    """
    try:
        tasks = await mongodb.list_tasks(limit=limit, skip=skip)
        return {
            "success": True,
            "tasks": tasks,
            "count": len(tasks)
        }
    except Exception as e:
        # MongoDB 不可用时返回空列表
        return {
            "success": False,
            "tasks": [],
            "count": 0,
            "error": str(e)
        }


@router.delete("/{task_id}")
async def delete_task(task_id: str):
    """
    删除任务

    Args:
        task_id: 任务ID

    Returns:
        是否删除成功
    """
    try:
        # 从 Redis 删除
        if redis_db._connected and redis_db.client:
            key = f"task:{task_id}"
            await redis_db.client.delete(key)

        # 从 MongoDB 删除
        deleted = await mongodb.delete_task(task_id)

        return {
            "success": True,
            "deleted": deleted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除任务失败: {str(e)}")
