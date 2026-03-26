"""
RAG 服务模块 - 检索增强生成

使用 LangChain + Faiss 实现向量检索
"""
import logging
import os
from typing import Any, Dict, List, Optional

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document as LangchainDocument
from langchain.vectorstores import FAISS

from app.config import settings

logger = logging.getLogger(__name__)


class RAGService:
    """RAG 检索增强服务"""

    def __init__(self):
        self.embeddings: Optional[HuggingFaceEmbeddings] = None
        self.vector_store: Optional[FAISS] = None
        self._initialized = False

    def _init_embeddings(self):
        """初始化嵌入模型"""
        if self.embeddings is None:
            self.embeddings = HuggingFaceEmbeddings(
                model_name=settings.EMBEDDING_MODEL,
                model_kwargs={'device': 'cpu'}
            )
            logger.info(f"RAG 嵌入模型初始化完成: {settings.EMBEDDING_MODEL}")

    def _init_vector_store(self):
        """初始化向量存储"""
        if self.vector_store is None:
            self._init_embeddings()
            self.vector_store = FAISS(
                embedding_function=self.embeddings,
                index=None,  # 创建一个空索引
                docstore={},
                index_to_docstore_id={}
            )
            logger.info("Faiss 向量存储初始化完成")

    async def initialize(self):
        """异步初始化"""
        try:
            self._init_vector_store()
            self._initialized = True
            logger.info("RAG 服务初始化成功")
        except Exception as e:
            logger.error(f"RAG 服务初始化失败: {e}")
            raise

    def index_field(
        self,
        table_name: str,
        field_name: str,
        field_description: str,
        sample_values: Optional[List[str]] = None
    ):
        """
        将字段信息索引到向量数据库

        Args:
            table_name: 表名
            field_name: 字段名
            field_description: 字段语义描述
            sample_values: 示例值
        """
        if not self._initialized:
            self._init_vector_store()

        # 构造完整文本
        text = f"表名: {table_name}, 字段: {field_name}, 描述: {field_description}"
        if sample_values:
            text += f", 示例值: {', '.join(sample_values)}"

        # 创建文档
        doc_id = f"{table_name}.{field_name}"
        doc = LangchainDocument(
            page_content=text,
            metadata={
                "table_name": table_name,
                "field_name": field_name,
                "doc_id": doc_id
            }
        )

        # 添加到向量存储
        if self.vector_store is None:
            self._init_vector_store()

        self.vector_store.add_documents([doc], ids=[doc_id])
        logger.debug(f"已索引字段: {doc_id}")

    def index_document_content(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        将文档内容索引到向量数据库

        Args:
            doc_id: 文档ID
            content: 文档内容
            metadata: 元数据
        """
        if not self._initialized:
            self._init_vector_store()

        doc = LangchainDocument(
            page_content=content,
            metadata=metadata or {"doc_id": doc_id}
        )

        if self.vector_store is None:
            self._init_vector_store()

        self.vector_store.add_documents([doc], ids=[doc_id])
        logger.debug(f"已索引文档: {doc_id}")

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        根据查询检索相关文档

        Args:
            query: 用户查询
            top_k: 返回数量

        Returns:
            相关文档列表
        """
        if not self._initialized:
            self._init_vector_store()

        if self.vector_store is None:
            return []

        # 执行相似度搜索
        docs_and_scores = self.vector_store.similarity_search_with_score(
            query,
            k=top_k
        )

        results = []
        for doc, score in docs_and_scores:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),  # 距离分数，越小越相似
                "doc_id": doc.metadata.get("doc_id", "")
            })

        logger.debug(f"检索到 {len(results)} 条相关文档")
        return results

    def retrieve_by_table(self, table_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        检索指定表的字段

        Args:
            table_name: 表名
            top_k: 返回数量

        Returns:
            相关字段列表
        """
        return self.retrieve(f"表名: {table_name}", top_k)

    def get_vector_count(self) -> int:
        """获取向量总数"""
        if self.vector_store is None:
            return 0
        return len(self.vector_store.docstore._dict)

    def save_index(self, persist_path: str):
        """
        保存向量索引到磁盘

        Args:
            persist_path: 保存路径
        """
        if self.vector_store is not None:
            self.vector_store.save_local(persist_path)
            logger.info(f"向量索引已保存到: {persist_path}")

    def load_index(self, persist_path: str):
        """
        从磁盘加载向量索引

        Args:
            persist_path: 保存路径
        """
        if not os.path.exists(persist_path):
            logger.warning(f"向量索引文件不存在: {persist_path}")
            return

        self._init_embeddings()
        self.vector_store = FAISS.load_local(
            persist_path,
            self.embeddings,
            allow_dangerous_deserialization=True
        )
        self._initialized = True
        logger.info(f"向量索引已从 {persist_path} 加载")

    def delete_by_doc_id(self, doc_id: str):
        """根据文档ID删除索引"""
        if self.vector_store is not None:
            self.vector_store.delete(ids=[doc_id])
            logger.debug(f"已删除索引: {doc_id}")

    def clear(self):
        """清空所有索引"""
        self._init_vector_store()
        if self.vector_store is not None:
            self.vector_store.delete(ids=list(self.vector_store.docstore._dict.keys()))
            logger.info("已清空所有向量索引")


# ==================== 全局单例 ====================

rag_service = RAGService()
