"""
RAG 检索 API 接口

提供向量检索功能
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["RAG检索"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


class SearchResult(BaseModel):
    content: str
    metadata: dict
    score: float
    doc_id: str


@router.post("/search")
async def search_rag(
    request: SearchRequest
):
    """
    RAG 语义检索

    根据查询文本检索相关的文档片段或字段

    Args:
        request.query: 查询文本
        request.top_k: 返回数量

    Returns:
        相关文档列表
    """
    try:
        results = rag_service.retrieve(
            query=request.query,
            top_k=request.top_k
        )

        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检索失败: {str(e)}")


@router.get("/status")
async def get_rag_status():
    """
    获取 RAG 索引状态

    Returns:
        RAG 索引统计信息
    """
    try:
        count = rag_service.get_vector_count()

        return {
            "success": True,
            "vector_count": count,
            "collections": ["document_fields", "document_content"]  # 预留
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取状态失败: {str(e)}")


@router.post("/rebuild")
async def rebuild_rag_index():
    """
    重建 RAG 索引

    从 MongoDB 中读取所有文档，重新构建向量索引
    """
    from app.core.database import mongodb

    try:
        # 清空现有索引
        rag_service.clear()

        # 从 MongoDB 读取所有文档
        cursor = mongodb.documents.find({})
        count = 0

        async for doc in cursor:
            content = doc.get("content", "")
            if content:
                rag_service.index_document_content(
                    doc_id=str(doc["_id"]),
                    content=content[:5000],
                    metadata={
                        "filename": doc.get("metadata", {}).get("filename"),
                        "doc_type": doc.get("doc_type")
                    }
                )
                count += 1

        return {
            "success": True,
            "message": f"已重建索引，共处理 {count} 个文档"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重建索引失败: {str(e)}")
