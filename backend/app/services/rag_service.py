"""
RAG 服务模块 - 检索增强生成

使用 sentence-transformers + Faiss 实现向量检索
"""
import json
import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import settings

logger = logging.getLogger(__name__)


class SimpleDocument:
    """简化文档对象"""
    def __init__(self, page_content: str, metadata: Dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata


class RAGService:
    """RAG 检索增强服务"""

    def __init__(self):
        self.embedding_model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.Index] = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []
        self._dimension: int = 0
        self._initialized = False
        self._persist_dir = settings.FAISS_INDEX_DIR

    def _init_embeddings(self):
        """初始化嵌入模型"""
        if self.embedding_model is None:
            self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)
            self._dimension = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"RAG 嵌入模型初始化完成: {settings.EMBEDDING_MODEL}, 维度: {self._dimension}")

    def _init_vector_store(self):
        """初始化向量存储"""
        if self.index is None:
            self._init_embeddings()
            self.index = faiss.IndexIDMap(faiss.IndexFlatIP(self._dimension))
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

    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """归一化向量"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        return vectors / norms

    def index_field(
        self,
        table_name: str,
        field_name: str,
        field_description: str,
        sample_values: Optional[List[str]] = None
    ):
        """将字段信息索引到向量数据库"""
        if not self._initialized:
            self._init_vector_store()

        text = f"表名: {table_name}, 字段: {field_name}, 描述: {field_description}"
        if sample_values:
            text += f", 示例值: {', '.join(sample_values)}"

        doc_id = f"{table_name}.{field_name}"
        doc = SimpleDocument(
            page_content=text,
            metadata={"table_name": table_name, "field_name": field_name, "doc_id": doc_id}
        )
        self._add_documents([doc], [doc_id])
        logger.debug(f"已索引字段: {doc_id}")

    def index_document_content(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """将文档内容索引到向量数据库"""
        if not self._initialized:
            self._init_vector_store()

        doc = SimpleDocument(
            page_content=content,
            metadata=metadata or {"doc_id": doc_id}
        )
        self._add_documents([doc], [doc_id])
        logger.debug(f"已索引文档: {doc_id}")

    def _add_documents(self, documents: List[SimpleDocument], doc_ids: List[str]):
        """批量添加文档到向量索引"""
        if not documents:
            return

        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        embeddings = self._normalize_vectors(embeddings).astype('float32')

        if self.index is None:
            self._init_vector_store()

        id_list = [hash(did) for did in doc_ids]
        id_array = np.array(id_list, dtype='int64')
        self.index.add_with_ids(embeddings, id_array)

        for doc, did in zip(documents, doc_ids):
            self.documents.append({"id": did, "content": doc.page_content, "metadata": doc.metadata})
            self.doc_ids.append(did)

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """根据查询检索相关文档"""
        if not self._initialized:
            self._init_vector_store()

        if self.index is None or self.index.ntotal == 0:
            return []

        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        query_embedding = self._normalize_vectors(query_embedding).astype('float32')

        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            doc = self.documents[idx]
            results.append({
                "content": doc["content"],
                "metadata": doc["metadata"],
                "score": float(score),
                "doc_id": doc["id"]
            })

        logger.debug(f"检索到 {len(results)} 条相关文档")
        return results

    def retrieve_by_table(self, table_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索指定表的字段"""
        return self.retrieve(f"表名: {table_name}", top_k)

    def get_vector_count(self) -> int:
        """获取向量总数"""
        if self.index is None:
            return 0
        return self.index.ntotal

    def save_index(self, persist_path: str = None):
        """保存向量索引到磁盘"""
        if persist_path is None:
            persist_path = self._persist_dir

        if self.index is not None:
            os.makedirs(persist_path, exist_ok=True)
            faiss.write_index(self.index, os.path.join(persist_path, "index.faiss"))
            with open(os.path.join(persist_path, "documents.pkl"), "wb") as f:
                pickle.dump(self.documents, f)
            logger.info(f"向量索引已保存到: {persist_path}")

    def load_index(self, persist_path: str = None):
        """从磁盘加载向量索引"""
        if persist_path is None:
            persist_path = self._persist_dir

        index_file = os.path.join(persist_path, "index.faiss")
        docs_file = os.path.join(persist_path, "documents.pkl")

        if not os.path.exists(index_file):
            logger.warning(f"向量索引文件不存在: {index_file}")
            return

        self._init_embeddings()
        self.index = faiss.read_index(index_file)

        with open(docs_file, "rb") as f:
            self.documents = pickle.load(f)

        self.doc_ids = [d["id"] for d in self.documents]
        self._initialized = True
        logger.info(f"向量索引已从 {persist_path} 加载，共 {len(self.documents)} 条")

    def delete_by_doc_id(self, doc_id: str):
        """根据文档ID删除索引"""
        if self.index is not None:
            remaining = [d for d in self.documents if d["id"] != doc_id]
            self.documents = remaining
            self.doc_ids = [d["id"] for d in self.documents]

            self.index.reset()
            if self.documents:
                texts = [d["content"] for d in self.documents]
                embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
                embeddings = self._normalize_vectors(embeddings).astype('float32')
                id_array = np.array([hash(did) for did in self.doc_ids], dtype='int64')
                self.index.add_with_ids(embeddings, id_array)

            logger.debug(f"已删除索引: {doc_id}")

    def clear(self):
        """清空所有索引"""
        self._init_vector_store()
        if self.index is not None:
            self.index.reset()
            self.documents = []
            self.doc_ids = []
            logger.info("已清空所有向量索引")


rag_service = RAGService()
