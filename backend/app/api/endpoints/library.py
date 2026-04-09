"""
文档库管理 API 接口

提供文档列表、详情查询和删除功能
"""
import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.database import mongodb

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["文档库"])


class DocumentItem(BaseModel):
    doc_id: str
    filename: str
    original_filename: str
    doc_type: str
    file_size: int
    created_at: str
    metadata: Optional[dict] = None


@router.get("")
async def get_documents(
    doc_type: Optional[str] = Query(None, description="文档类型过滤"),
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
    skip: int = Query(0, ge=0, description="跳过数量")
):
    """
    获取文档列表

    Returns:
        文档列表
    """
    try:
        # 构建查询条件
        query = {}
        if doc_type:
            query["doc_type"] = doc_type

        logger.info(f"开始查询文档列表, query: {query}, limit: {limit}")

        # 使用 batch_size 和 max_time_ms 来控制查询
        cursor = mongodb.documents.find(
            query,
            {"content": 0}  # 不返回 content 字段，减少数据传输
        ).sort("created_at", -1).skip(skip).limit(limit)

        # 设置 10 秒超时
        cursor.max_time_ms(10000)

        logger.info("Cursor created with 10s timeout, executing...")

        # 使用 batch_size 逐批获取
        documents_raw = await cursor.to_list(length=limit)
        logger.info(f"查询到原始文档数: {len(documents_raw)}")

        documents = []
        for doc in documents_raw:
            documents.append({
                "doc_id": str(doc["_id"]),
                "filename": doc.get("metadata", {}).get("filename", ""),
                "original_filename": doc.get("metadata", {}).get("original_filename", ""),
                "doc_type": doc.get("doc_type", ""),
                "file_size": doc.get("metadata", {}).get("file_size", 0),
                "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
                "metadata": {
                    "row_count": doc.get("metadata", {}).get("row_count"),
                    "column_count": doc.get("metadata", {}).get("column_count"),
                    "columns": doc.get("metadata", {}).get("columns", [])[:10]
                }
            })

        logger.info(f"文档列表处理完成: {len(documents)} 个文档")

        return {
            "success": True,
            "documents": documents,
            "total": len(documents)
        }

    except Exception as e:
        err_str = str(e)
        # 如果是超时错误，返回空列表而不是报错
        if "timeout" in err_str.lower() or "time" in err_str.lower():
            logger.warning(f"文档查询超时，返回空列表: {err_str}")
            return {
                "success": True,
                "documents": [],
                "total": 0,
                "warning": "查询超时，请稍后重试"
            }
        logger.error(f"获取文档列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/{doc_id}")
async def get_document(doc_id: str):
    """
    获取文档详情

    Args:
        doc_id: 文档ID

    Returns:
        文档详情
    """
    try:
        doc = await mongodb.get_document(doc_id)

        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        return {
            "success": True,
            "document": {
                "doc_id": str(doc["_id"]),
                "filename": doc.get("metadata", {}).get("filename", ""),
                "original_filename": doc.get("metadata", {}).get("original_filename", ""),
                "doc_type": doc.get("doc_type", ""),
                "file_size": doc.get("metadata", {}).get("file_size", 0),
                "created_at": doc.get("created_at", "").isoformat() if doc.get("created_at") else "",
                "content": doc.get("content", ""),  # 原始文本内容
                "structured_data": doc.get("structured_data"),  # 结构化数据(如果有)
                "metadata": doc.get("metadata", {})
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文档详情失败: {str(e)}")


@router.delete("/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除文档

    Args:
        doc_id: 文档ID

    Returns:
        删除结果
    """
    try:
        # 从 MongoDB 删除
        deleted = await mongodb.delete_document(doc_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="文档不存在")

        # TODO: 从 MySQL 删除相关数据(如果是Excel)
        # TODO: 从 RAG 删除相关索引

        return {
            "success": True,
            "message": "文档已删除"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")
