"""
RAG 服务模块 - 检索增强生成

使用 sentence-transformers + Faiss 实现向量检索
"""
import logging
import os
import pickle
from typing import Any, Dict, List, Optional

import faiss
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# 尝试导入 sentence-transformers
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"sentence-transformers 导入失败: {e}")
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class SimpleDocument:
    """简化文档对象"""
    def __init__(self, page_content: str, metadata: Dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata


class RAGService:
    """RAG 检索增强服务"""

    # 默认分块参数
    DEFAULT_CHUNK_SIZE = 500  # 每个文本块的大小（字符数）
    DEFAULT_CHUNK_OVERLAP = 50  # 块之间的重叠（字符数）

    def __init__(self):
        self.embedding_model = None
        self.index: Optional[faiss.Index] = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []
        self._dimension: int = 384  # 默认维度
        self._initialized = False
        self._persist_dir = settings.FAISS_INDEX_DIR
        # 检查是否可用
        self._disabled = not SENTENCE_TRANSFORMERS_AVAILABLE
        if self._disabled:
            logger.warning("RAG 服务已禁用（sentence-transformers 不可用），将使用关键词匹配作为后备")
        else:
            logger.info("RAG 服务已启用")

    def _init_embeddings(self):
        """初始化嵌入模型"""
        if self._disabled:
            logger.debug("RAG 已禁用，跳过嵌入模型初始化")
            return
        if self.embedding_model is None:
            # 使用轻量级本地模型，避免网络问题
            model_name = 'all-MiniLM-L6-v2'
            try:
                self.embedding_model = SentenceTransformer(model_name)
                self._dimension = self.embedding_model.get_sentence_embedding_dimension()
                logger.info(f"RAG 嵌入模型初始化完成: {model_name}, 维度: {self._dimension}")
            except Exception as e:
                logger.warning(f"嵌入模型 {model_name} 加载失败: {e}")
                # 如果本地模型也失败，使用简单hash作为后备
                self.embedding_model = None
                self._dimension = 384
                logger.info("RAG 使用简化模式 (无向量嵌入)")

    def _init_vector_store(self):
        """初始化向量存储"""
        if self.index is None:
            self._init_embeddings()
            if self.embedding_model is None:
                # 无法加载嵌入模型，使用简化模式
                self._dimension = 384
                self.index = None
                logger.warning("RAG 嵌入模型未加载，使用简化模式")
            else:
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

    def _split_into_chunks(self, text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        将长文本分割成块

        Args:
            text: 待分割的文本
            chunk_size: 每个块的大小（字符数）
            overlap: 块之间的重叠字符数

        Returns:
            文本块列表
        """
        if chunk_size is None:
            chunk_size = self.DEFAULT_CHUNK_SIZE
        if overlap is None:
            overlap = self.DEFAULT_CHUNK_OVERLAP

        if len(text) <= chunk_size:
            return [text] if text.strip() else []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            # 计算当前块的结束位置
            end = start + chunk_size

            # 如果不是最后一块，尝试在句子边界处切割
            if end < text_len:
                # 向前查找最后一个句号、逗号、换行或分号
                cut_positions = []
                for i in range(end, max(start, end - 100), -1):
                    if text[i] in '。；，,\n、':
                        cut_positions.append(i + 1)
                        break

                if cut_positions:
                    end = cut_positions[0]
                else:
                    # 如果没找到句子边界，尝试向后查找
                    for i in range(end, min(text_len, end + 50)):
                        if text[i] in '。；，,\n、':
                            end = i + 1
                            break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            # 移动起始位置（考虑重叠）
            start = end - overlap
            if start <= 0:
                start = end

        return chunks

    def index_field(
        self,
        table_name: str,
        field_name: str,
        field_description: str,
        sample_values: Optional[List[str]] = None
    ):
        """将字段信息索引到向量数据库"""
        if self._disabled:
            logger.info(f"[RAG DISABLED] 字段索引操作已跳过: {table_name}.{field_name}")
            return

        if not self._initialized:
            self._init_vector_store()

        # 如果没有嵌入模型，只记录到日志
        if self.embedding_model is None:
            logger.debug(f"字段跳过索引 (无嵌入模型): {table_name}.{field_name}")
            return

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
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        将文档内容索引到向量数据库（自动分块）

        Args:
            doc_id: 文档唯一标识
            content: 文档内容
            metadata: 文档元数据
            chunk_size: 文本块大小（字符数），默认500
            chunk_overlap: 块之间的重叠字符数，默认50
        """
        if self._disabled:
            logger.info(f"[RAG DISABLED] 文档索引操作已跳过: {doc_id}")
            return

        if not self._initialized:
            self._init_vector_store()

        # 如果没有嵌入模型，只记录到日志
        if self.embedding_model is None:
            logger.debug(f"文档跳过索引 (无嵌入模型): {doc_id}")
            return

        # 分割文档为小块
        if chunk_size is None:
            chunk_size = self.DEFAULT_CHUNK_SIZE
        if chunk_overlap is None:
            chunk_overlap = self.DEFAULT_CHUNK_OVERLAP

        chunks = self._split_into_chunks(content, chunk_size, chunk_overlap)

        if not chunks:
            logger.warning(f"文档内容为空，跳过索引: {doc_id}")
            return

        # 为每个块创建文档对象
        documents = []
        chunk_ids = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                "chunk_index": i,
                "total_chunks": len(chunks),
                "doc_id": doc_id
            })

            documents.append(SimpleDocument(
                page_content=chunk,
                metadata=chunk_metadata
            ))
            chunk_ids.append(chunk_id)

        # 批量添加文档
        self._add_documents(documents, chunk_ids)
        logger.info(f"已索引文档 {doc_id}，共 {len(chunks)} 个块")

    def _add_documents(self, documents: List[SimpleDocument], doc_ids: List[str]):
        """批量添加文档到向量索引"""
        if not documents:
            return

        # 总是将文档存储在内存中（用于关键词搜索后备）
        for doc, did in zip(documents, doc_ids):
            self.documents.append({"id": did, "content": doc.page_content, "metadata": doc.metadata})
            self.doc_ids.append(did)

        # 如果没有嵌入模型，跳过向量索引
        if self.embedding_model is None:
            logger.debug(f"文档跳过向量索引 (无嵌入模型): {len(documents)} 个文档")
            return

        texts = [doc.page_content for doc in documents]
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)
        embeddings = self._normalize_vectors(embeddings).astype('float32')

        if self.index is None:
            self._init_vector_store()

        id_list = [hash(did) for did in doc_ids]
        id_array = np.array(id_list, dtype='int64')
        self.index.add_with_ids(embeddings, id_array)

    def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.3) -> List[Dict[str, Any]]:
        """
        根据查询检索相关文档块

        Args:
            query: 查询文本
            top_k: 返回的最大结果数
            min_score: 最低相似度分数阈值

        Returns:
            相关文档块列表，每项包含 content, metadata, score, doc_id, chunk_index
        """
        if self._disabled:
            logger.info(f"[RAG DISABLED] 检索操作已跳过: query={query}, top_k={top_k}")
            return []

        if not self._initialized:
            self._init_vector_store()

        # 优先使用向量检索
        if self.index is not None and self.index.ntotal > 0 and self.embedding_model is not None:
            try:
                query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
                query_embedding = self._normalize_vectors(query_embedding).astype('float32')

                scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx < 0:
                        continue
                    if score < min_score:
                        continue
                    doc = self.documents[idx]
                    results.append({
                        "content": doc["content"],
                        "metadata": doc["metadata"],
                        "score": float(score),
                        "doc_id": doc["id"],
                        "chunk_index": doc["metadata"].get("chunk_index", 0)
                    })

                if results:
                    logger.debug(f"向量检索到 {len(results)} 条相关文档块")
                    return results
            except Exception as e:
                logger.warning(f"向量检索失败，使用关键词搜索后备: {e}")

        # 后备：使用关键词搜索
        logger.debug("使用关键词搜索后备方案")
        return self._keyword_search(query, top_k)

    def _keyword_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        关键词搜索后备方案

        Args:
            query: 查询文本
            top_k: 返回的最大结果数

        Returns:
            相关文档块列表
        """
        if not self.documents:
            return []

        # 提取查询关键词
        keywords = []
        for char in query:
            if '\u4e00' <= char <= '\u9fff':  # 中文字符
                keywords.append(char)
        # 添加英文单词
        import re
        english_words = re.findall(r'[a-zA-Z]+', query)
        keywords.extend(english_words)

        if not keywords:
            return []

        results = []
        for doc in self.documents:
            content = doc["content"]
            # 计算关键词匹配分数
            score = 0
            matched_keywords = 0
            for kw in keywords:
                if kw in content:
                    score += 1
                    matched_keywords += 1

            if matched_keywords > 0:
                # 归一化分数
                score = score / max(len(keywords), 1)
                results.append({
                    "content": content,
                    "metadata": doc["metadata"],
                    "score": score,
                    "doc_id": doc["id"],
                    "chunk_index": doc["metadata"].get("chunk_index", 0)
                })

        # 按分数排序
        results.sort(key=lambda x: x["score"], reverse=True)

        logger.debug(f"关键词搜索返回 {len(results[:top_k])} 条结果")
        return results[:top_k]

    def retrieve_by_doc_id(self, doc_id: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        获取指定文档的所有块

        Args:
            doc_id: 文档ID
            top_k: 返回的最大结果数

        Returns:
            该文档的所有块
        """
        # 获取属于该文档的所有块
        doc_chunks = [d for d in self.documents if d["metadata"].get("doc_id") == doc_id]

        # 按 chunk_index 排序
        doc_chunks.sort(key=lambda x: x["metadata"].get("chunk_index", 0))

        # 返回指定数量
        return doc_chunks[:top_k]

    def retrieve_by_table(self, table_name: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """检索指定表的字段"""
        return self.retrieve(f"表名: {table_name}", top_k)

    def get_vector_count(self) -> int:
        """获取向量总数"""
        if self._disabled:
            logger.info("[RAG DISABLED] get_vector_count 返回 0")
            return 0
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
        if self._disabled:
            logger.info("[RAG DISABLED] clear 操作已跳过")
            return
        self._init_vector_store()
        if self.index is not None:
            self.index.reset()
            self.documents = []
            self.doc_ids = []
            logger.info("已清空所有向量索引")


rag_service = RAGService()
