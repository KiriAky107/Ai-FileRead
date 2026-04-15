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
                serverSelectionTimeoutMS=30000,  # 30秒超时，适应远程服务器
                connectTimeoutMS=30000,  # 连接超时
                socketTimeoutMS=60000,  # Socket 超时
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

    @property
    def tasks(self):
        """任务集合 - 存储任务历史记录"""
        return self.db["tasks"]

    @property
    def conversations(self):
        """对话集合 - 存储对话历史记录"""
        return self.db["conversations"]

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
        doc_id = str(result.inserted_id)
        filename = metadata.get("original_filename", "unknown")
        logger.info(f"✓ 文档已存入MongoDB: [{doc_type}] {filename} | ID: {doc_id}")
        return doc_id

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
            query: 搜索关键词（支持文件名和内容搜索）
            doc_type: 文档类型过滤
            limit: 返回数量

        Returns:
            文档列表
        """
        filter_query = {
            "$or": [
                {"content": {"$regex": query, "$options": "i"}},
                {"metadata.original_filename": {"$regex": query, "$options": "i"}},
                {"metadata.filename": {"$regex": query, "$options": "i"}},
            ]
        }
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

    async def update_document_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> bool:
        """更新文档 metadata 字段"""
        from bson import ObjectId
        result = await self.documents.update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"metadata": metadata}}
        )
        return result.modified_count > 0

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

        # 任务集合索引
        await self.tasks.create_index("task_id", unique=True)
        await self.tasks.create_index("created_at")

        # 对话集合索引
        await self.conversations.create_index("conversation_id")
        await self.conversations.create_index("created_at")

        logger.info("MongoDB 索引创建完成")

    # ==================== 任务历史操作 ====================

    async def insert_task(
        self,
        task_id: str,
        task_type: str,
        status: str = "pending",
        message: str = "",
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> str:
        """
        插入任务记录

        Args:
            task_id: 任务ID
            task_type: 任务类型
            status: 任务状态
            message: 任务消息
            result: 任务结果
            error: 错误信息

        Returns:
            插入文档的ID
        """
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "status": status,
            "message": message,
            "result": result,
            "error": error,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result_obj = await self.tasks.insert_one(task)
        return str(result_obj.inserted_id)

    async def update_task(
        self,
        task_id: str,
        status: Optional[str] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        更新任务状态

        Args:
            task_id: 任务ID
            status: 任务状态
            message: 任务消息
            result: 任务结果
            error: 错误信息

        Returns:
            是否更新成功
        """
        from bson import ObjectId

        update_data = {"updated_at": datetime.utcnow()}
        if status is not None:
            update_data["status"] = status
        if message is not None:
            update_data["message"] = message
        if result is not None:
            update_data["result"] = result
        if error is not None:
            update_data["error"] = error

        update_result = await self.tasks.update_one(
            {"task_id": task_id},
            {"$set": update_data}
        )
        return update_result.modified_count > 0

    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """根据task_id获取任务"""
        task = await self.tasks.find_one({"task_id": task_id})
        if task:
            task["_id"] = str(task["_id"])
        return task

    async def list_tasks(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取任务列表

        Args:
            limit: 返回数量
            skip: 跳过数量

        Returns:
            任务列表
        """
        cursor = self.tasks.find().sort("created_at", -1).skip(skip).limit(limit)
        tasks = []
        async for task in cursor:
            task["_id"] = str(task["_id"])
            # 转换 datetime 为字符串
            if task.get("created_at"):
                task["created_at"] = task["created_at"].isoformat()
            if task.get("updated_at"):
                task["updated_at"] = task["updated_at"].isoformat()
            tasks.append(task)
        return tasks

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        result = await self.tasks.delete_one({"task_id": task_id})
        return result.deleted_count > 0

    # ==================== 对话历史操作 ====================

    async def insert_conversation(
        self,
        conversation_id: str,
        role: str,
        content: str,
        intent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        插入对话记录

        Args:
            conversation_id: 对话会话ID
            role: 角色 (user/assistant)
            content: 对话内容
            intent: 意图类型
            metadata: 额外元数据

        Returns:
            插入文档的ID
        """
        message = {
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "intent": intent,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
        }
        result = await self.conversations.insert_one(message)
        return str(result.inserted_id)

    async def get_conversation_history(
        self,
        conversation_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Args:
            conversation_id: 对话会话ID
            limit: 返回消息数量

        Returns:
            对话消息列表
        """
        cursor = self.conversations.find(
            {"conversation_id": conversation_id}
        ).sort("created_at", 1).limit(limit)

        messages = []
        async for msg in cursor:
            msg["_id"] = str(msg["_id"])
            if msg.get("created_at"):
                msg["created_at"] = msg["created_at"].isoformat()
            messages.append(msg)
        return messages

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话会话"""
        result = await self.conversations.delete_many({"conversation_id": conversation_id})
        return result.deleted_count > 0

    async def list_conversations(
        self,
        limit: int = 50,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        获取会话列表（按最近一条消息排序）

        Args:
            limit: 返回数量
            skip: 跳过数量

        Returns:
            会话列表
        """
        # 使用 aggregation 获取每个会话的最新一条消息
        pipeline = [
            {"$sort": {"created_at": -1}},
            {"$group": {
                "_id": "$conversation_id",
                "last_message": {"$first": "$$ROOT"},
            }},
            {"$replaceRoot": {"newRoot": "$last_message"}},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit},
        ]

        conversations = []
        async for doc in self.conversations.aggregate(pipeline):
            doc["_id"] = str(doc["_id"])
            if doc.get("created_at"):
                doc["created_at"] = doc["created_at"].isoformat()
            conversations.append(doc)
        return conversations


# ==================== 全局单例 ====================

mongodb = MongoDB()
