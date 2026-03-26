"""
MongoDB 数据库连接管理模块

提供非结构化数据的存储和查询功能
"""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import settings

logger = logging.getLogger(__name__)


class MongoDB:
    """MongoDB 数据库管理类"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self):
        """建立 MongoDB 连接"""
        try:
            self.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000,
            )
            self.db = self.client[settings.MONGODB_DB_NAME]
            # 验证连接
            await self.client.admin.command('ping')
            logger.info(f"MongoDB 连接成功: {settings.MONGODB_DB_NAME}")
        except Exception as e:
            logger.error(f"MongoDB 连接失败: {e}")
            raise

    async def close(self):
        """关闭 MongoDB 连接"""
        if self.client:
            self.client.close()
            logger.info("MongoDB 连接已关闭")

    @property
    def documents(self):
        """文档集合 - 存储原始文档和解析结果"""
        return self.db["documents"]

    @property
    def embeddings(self):
        """向量嵌入集合 - 存储文本嵌入向量"""
        return self.db["embeddings"]

    @property
    def rag_index(self):
        """RAG索引集合 - 存储字段语义索引"""
        return self.db["rag_index"]

    # ==================== 文档操作 ====================

    async def insert_document(
        self,
        doc_type: str,
        content: str,
        metadata: Dict[str, Any],
        structured_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        插入文档

        Args:
            doc_type: 文档类型 (docx/xlsx/md/txt)
            content: 原始文本内容
            metadata: 元数据
            structured_data: 结构化数据 (表格等)

        Returns:
            插入文档的ID
        """
        document = {
            "doc_type": doc_type,
            "content": content,
            "metadata": metadata,
            "structured_data": structured_data,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = await self.documents.insert_one(document)
        logger.info(f"文档已插入MongoDB: {result.inserted_id}")
        return str(result.inserted_id)

    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """根据ID获取文档"""
        from bson import ObjectId
        doc = await self.documents.find_one({"_id": ObjectId(doc_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
        return doc

    async def search_documents(
        self,
        query: str,
        doc_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索文档

        Args:
            query: 搜索关键词
            doc_type: 文档类型过滤
            limit: 返回数量

        Returns:
            文档列表
        """
        filter_query = {"content": {"$regex": query}}
        if doc_type:
            filter_query["doc_type"] = doc_type

        cursor = self.documents.find(filter_query).limit(limit)
        documents = []
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            documents.append(doc)
        return documents

    async def delete_document(self, doc_id: str) -> bool:
        """删除文档"""
        from bson import ObjectId
        result = await self.documents.delete_one({"_id": ObjectId(doc_id)})
        return result.deleted_count > 0

    # ==================== RAG 索引操作 ====================

    async def insert_rag_entry(
        self,
        table_name: str,
        field_name: str,
        field_description: str,
        embedding: List[float],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        插入RAG索引条目

        Args:
            table_name: 表名
            field_name: 字段名
            field_description: 字段描述
            embedding: 向量嵌入
            metadata: 其他元数据

        Returns:
            插入条目的ID
        """
        entry = {
            "table_name": table_name,
            "field_name": field_name,
            "field_description": field_description,
            "embedding": embedding,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        result = await self.rag_index.insert_one(entry)
        return str(result.inserted_id)

    async def search_rag(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        table_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索RAG索引 (使用向量相似度)

        Args:
            query_embedding: 查询向量
            top_k: 返回数量
            table_name: 可选的表名过滤

        Returns:
            相关的索引条目
        """
        # MongoDB 5.0+ 支持向量搜索
        # 较低版本使用欧氏距离替代
        pipeline = [
            {
                "$addFields": {
                    "distance": {
                        "$reduce": {
                            "input": {"$range": [0, {"$size": "$embedding"}]},
                            "initialValue": 0,
                            "in": {
                                "$add": [
                                    "$$value",
                                    {
                                        "$pow": [
                                            {
                                                "$subtract": [
                                                    {"$arrayElemAt": ["$embedding", "$$this"]},
                                                    {"$arrayElemAt": [query_embedding, "$$this"]},
                                                ]
                                            },
                                            2,
                                        ]
                                    },
                                ]
                            },
                        }
                    }
                }
            },
            {"$sort": {"distance": 1}},
            {"$limit": top_k},
        ]

        if table_name:
            pipeline.insert(0, {"$match": {"table_name": table_name}})

        results = []
        async for doc in self.rag_index.aggregate(pipeline):
            doc["_id"] = str(doc["_id"])
            results.append(doc)
        return results

    # ==================== 集合管理 ====================

    async def create_indexes(self):
        """创建索引以优化查询"""
        # 文档集合索引
        await self.documents.create_index("doc_type")
        await self.documents.create_index("created_at")
        await self.documents.create_index([("content", "text")])

        # RAG索引集合索引
        await self.rag_index.create_index("table_name")
        await self.rag_index.create_index("field_name")
        await self.rag_index.create_index([("embedding", "hnsw", {"type": "knnVector"})])

        logger.info("MongoDB 索引创建完成")


# ==================== 全局单例 ====================

mongodb = MongoDB()
