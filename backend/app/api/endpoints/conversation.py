"""
对话历史 API 接口

提供对话历史的存储和查询功能
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import mongodb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["对话历史"])


# ==================== 请求/响应模型 ====================

class ConversationMessage(BaseModel):
    role: str
    content: str
    intent: Optional[str] = None


class ConversationHistoryResponse(BaseModel):
    success: bool
    messages: list


class ConversationListResponse(BaseModel):
    success: bool
    conversations: list


# ==================== 接口 ====================

@router.get("/{conversation_id}/history", response_model=ConversationHistoryResponse)
async def get_conversation_history(conversation_id: str, limit: int = 20):
    """
    获取对话历史

    Args:
        conversation_id: 对话会话ID
        limit: 返回消息数量（默认20条）
    """
    try:
        messages = await mongodb.get_conversation_history(conversation_id, limit=limit)
        return ConversationHistoryResponse(
            success=True,
            messages=messages
        )
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}")
        return ConversationHistoryResponse(
            success=False,
            messages=[]
        )


@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    删除对话会话

    Args:
        conversation_id: 对话会话ID
    """
    try:
        success = await mongodb.delete_conversation(conversation_id)
        return {"success": success}
    except Exception as e:
        logger.error(f"删除对话失败: {e}")
        return {"success": False, "error": str(e)}


@router.get("/all", response_model=ConversationListResponse)
async def list_conversations(limit: int = 50, skip: int = 0):
    """
    获取会话列表

    Args:
        limit: 返回数量
        skip: 跳过数量
    """
    try:
        conversations = await mongodb.list_conversations(limit=limit, skip=skip)
        return ConversationListResponse(
            success=True,
            conversations=conversations
        )
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        return ConversationListResponse(
            success=False,
            conversations=[]
        )