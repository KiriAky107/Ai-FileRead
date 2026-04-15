"""
RAG 服务模块 - 检索增强生成

使用 sentence-transformers + Faiss 实现向量检索
支持 BM25 关键词检索 + 向量检索混合融合
"""
import logging
import os
import pickle
import re
import math
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter, defaultdict

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


class BM25:
    """
    BM25 关键词检索算法

    一种基于词频和文档频率的信息检索算法，比纯向量搜索更适合关键词精确匹配
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1  # 词频饱和参数
        self.b = b    # 文档长度归一化参数
        self.documents: List[str] = []
        self.doc_ids: List[str] = []
        self.avg_doc_length = 0
        self.doc_freqs: Dict[str, int] = {}  # 词 -> 包含该词的文档数
        self.idf: Dict[str, float] = {}      # 词 -> IDF 值
        self.doc_lengths: List[int] = []
        self.doc_term_freqs: List[Dict[str, int]] = []  # 每个文档的词频

    def _tokenize(self, text: str) -> List[str]:
        """分词（简单的中文分词）"""
        if not text:
            return []
        # 简单分词：按标点和空格分割
        tokens = re.findall(r'[\u4e00-\u9fff]+|[a-zA-Z0-9]+', text.lower())
        # 过滤单字符
        return [t for t in tokens if len(t) > 1]

    def fit(self, documents: List[str], doc_ids: List[str]):
        """
        构建 BM25 索引

        Args:
            documents: 文档内容列表
            doc_ids: 文档 ID 列表
        """
        self.documents = documents
        self.doc_ids = doc_ids
        n = len(documents)

        # 统计文档频率
        self.doc_freqs = defaultdict(int)
        self.doc_lengths = []
        self.doc_term_freqs = []

        for doc in documents:
            tokens = self._tokenize(doc)
            self.doc_lengths.append(len(tokens))
            doc_tf = Counter(tokens)
            self.doc_term_freqs.append(doc_tf)

            for term in doc_tf:
                self.doc_freqs[term] += 1

        # 计算平均文档长度
        self.avg_doc_length = sum(self.doc_lengths) / n if n > 0 else 0

        # 计算 IDF
        for term, df in self.doc_freqs.items():
            # IDF = log((n - df + 0.5) / (df + 0.5))
            self.idf[term] = math.log((n - df + 0.5) / (df + 0.5) + 1)

        logger.info(f"BM25 索引构建完成: {n} 个文档, {len(self.idf)} 个词项")

    def search(self, query: str, top_k: int = 10) -> List[Tuple[int, float]]:
        """
        搜索相关文档

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果

        Returns:
            [(文档索引, BM25分数), ...]
        """
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = []
        n = len(self.documents)

        for idx in range(n):
            score = self._calculate_score(query_tokens, idx)
            scores.append((idx, score))

        # 按分数降序排序
        scores.sort(key=lambda x: x[1], reverse=True)

        return scores[:top_k]

    def _calculate_score(self, query_tokens: List[str], doc_idx: int) -> float:
        """计算单个文档的 BM25 分数"""
        doc_tf = self.doc_term_freqs[doc_idx]
        doc_len = self.doc_lengths[doc_idx]
        score = 0.0

        for term in query_tokens:
            if term not in self.idf:
                continue

            tf = doc_tf.get(term, 0)
            idf = self.idf[term]

            # BM25 公式
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)

            score += idf * numerator / denominator

        return score

    def get_scores(self, query: str) -> List[float]:
        """获取所有文档的 BM25 分数"""
        if not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return [0.0] * len(self.documents)

        return [self._calculate_score(query_tokens, idx) for idx in range(len(self.documents))]


class RAGService:
    """RAG 检索增强服务"""

    # 默认分块参数 - 增大块大小减少embedding次数
    DEFAULT_CHUNK_SIZE = 1000  # 每个文本块的大小（字符数），增大以提升速度
    DEFAULT_CHUNK_OVERLAP = 100  # 块之间的重叠（字符数）

    def __init__(self):
        self.embedding_model = None
        self.index: Optional[faiss.Index] = None
        self.documents: List[Dict[str, Any]] = []
        self.doc_ids: List[str] = []
        self._dimension: int = 384  # 默认维度
        self._initialized = False
        self._persist_dir = settings.FAISS_INDEX_DIR
        # BM25 索引
        self.bm25: Optional[BM25] = None
        self._bm25_enabled = True  # 始终启用 BM25
        # 检查是否可用
        self._disabled = not SENTENCE_TRANSFORMERS_AVAILABLE
        if self._disabled:
            logger.warning("RAG 服务已禁用（sentence-transformers 不可用），将使用 BM25 关键词检索")
        else:
            logger.info("RAG 服务已启用（向量检索 + BM25 混合检索）")

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

    async def index_document_content_async(
        self,
        doc_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = None,
        chunk_overlap: int = None
    ):
        """
        异步将文档内容索引到向量数据库（自动分块）

        使用 asyncio.to_thread 避免阻塞事件循环
        """
        import asyncio

        if self._disabled:
            logger.info(f"[RAG DISABLED] 文档索引操作已跳过: {doc_id}")
            return

        if not self._initialized:
            self._init_vector_store()

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

        # 使用线程池执行 CPU 密集型的 embedding 计算
        def _sync_add():
            self._add_documents(documents, chunk_ids)

        await asyncio.to_thread(_sync_add)
        logger.info(f"已异步索引文档 {doc_id}，共 {len(chunks)} 个块")

    def _add_documents(self, documents: List[SimpleDocument], doc_ids: List[str]):
        """批量添加文档到向量索引"""
        if not documents:
            return

        # 总是将文档存储在内存中（用于 BM25 和关键词搜索）
        for doc, did in zip(documents, doc_ids):
            self.documents.append({"id": did, "content": doc.page_content, "metadata": doc.metadata})
            self.doc_ids.append(did)

        # 构建 BM25 索引
        if self._bm25_enabled and documents:
            bm25_texts = [doc.page_content for doc in documents]
            if self.bm25 is None:
                self.bm25 = BM25()
                self.bm25.fit(bm25_texts, doc_ids)
            else:
                # 增量添加：重新构建（BM25 不支持增量）
                all_texts = [d["content"] for d in self.documents]
                all_ids = self.doc_ids.copy()
                self.bm25 = BM25()
                self.bm25.fit(all_texts, all_ids)
            logger.debug(f"BM25 索引更新: {len(documents)} 个文档")

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
        根据查询检索相关文档块（混合检索：向量 + BM25）

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

        # 获取向量检索结果
        vector_results = self._vector_search(query, top_k * 2, min_score)

        # 获取 BM25 检索结果
        bm25_results = self._bm25_search(query, top_k * 2)

        # 混合融合
        hybrid_results = self._hybrid_fusion(vector_results, bm25_results, top_k)

        if hybrid_results:
            logger.info(f"混合检索到 {len(hybrid_results)} 条相关文档块 (向量:{len(vector_results)}, BM25:{len(bm25_results)})")
            return hybrid_results

        # 降级：只使用 BM25
        if bm25_results:
            logger.info(f"降级到 BM25 检索: {len(bm25_results)} 条")
            return bm25_results

        # 降级：使用关键词搜索
        logger.info("降级到关键词搜索")
        return self._keyword_search(query, top_k)

    def _vector_search(self, query: str, top_k: int, min_score: float) -> List[Dict[str, Any]]:
        """向量检索"""
        if self.index is None or self.index.ntotal == 0 or self.embedding_model is None:
            return []

        try:
            query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
            query_embedding = self._normalize_vectors(query_embedding).astype('float32')

            scores, indices = self.index.search(query_embedding, min(top_k * 2, self.index.ntotal))

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
                    "chunk_index": doc["metadata"].get("chunk_index", 0),
                    "search_type": "vector"
                })

            return results
        except Exception as e:
            logger.warning(f"向量检索失败: {e}")
            return []

    def _bm25_search(self, query: str, top_k: int) -> List[Dict[str, Any]]:
        """BM25 检索"""
        if not self.bm25 or not self.documents:
            return []

        try:
            bm25_scores = self.bm25.get_scores(query)
            if not bm25_scores:
                return []

            # 归一化 BM25 分数到 [0, 1]
            max_score = max(bm25_scores) if bm25_scores else 1
            min_score_bm = min(bm25_scores) if bm25_scores else 0
            score_range = max_score - min_score_bm if max_score != min_score_bm else 1

            results = []
            for idx, score in enumerate(bm25_scores):
                if score <= 0:
                    continue
                # 归一化
                normalized_score = (score - min_score_bm) / score_range if score_range > 0 else 0
                doc = self.documents[idx]
                results.append({
                    "content": doc["content"],
                    "metadata": doc["metadata"],
                    "score": float(normalized_score),
                    "doc_id": doc["id"],
                    "chunk_index": doc["metadata"].get("chunk_index", 0),
                    "search_type": "bm25"
                })

            # 按分数降序
            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]

        except Exception as e:
            logger.warning(f"BM25 检索失败: {e}")
            return []

    def _hybrid_fusion(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        混合融合向量和 BM25 检索结果

        使用 RRFR (Reciprocal Rank Fusion) 算法:
        Score = weight_vector * (1 / rank_vector) + weight_bm25 * (1 / rank_bm25)

        Args:
            vector_results: 向量检索结果
            bm25_results: BM25 检索结果
            top_k: 返回数量

        Returns:
            融合后的结果
        """
        if not vector_results and not bm25_results:
            return []

        # 融合权重
        weight_vector = 0.6
        weight_bm25 = 0.4

        # 构建文档分数映射
        doc_scores: Dict[str, Dict[str, float]] = {}

        # 添加向量检索结果
        for rank, result in enumerate(vector_results):
            doc_id = result["doc_id"]
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"vector": 0, "bm25": 0, "content": result["content"], "metadata": result["metadata"]}
            # 使用倒数排名 (Reciprocal Rank)
            doc_scores[doc_id]["vector"] = weight_vector / (rank + 1)

        # 添加 BM25 检索结果
        for rank, result in enumerate(bm25_results):
            doc_id = result["doc_id"]
            if doc_id not in doc_scores:
                doc_scores[doc_id] = {"vector": 0, "bm25": 0, "content": result["content"], "metadata": result["metadata"]}
            doc_scores[doc_id]["bm25"] = weight_bm25 / (rank + 1)

        # 计算融合分数
        fused_results = []
        for doc_id, scores in doc_scores.items():
            fused_score = scores["vector"] + scores["bm25"]
            # 使用向量检索结果的原始分数作为参考
            vector_score = next((r["score"] for r in vector_results if r["doc_id"] == doc_id), 0.5)
            fused_results.append({
                "content": scores["content"],
                "metadata": scores["metadata"],
                "score": fused_score,
                "doc_id": doc_id,
                "vector_score": vector_score,
                "bm25_score": scores["bm25"],
                "search_type": "hybrid"
            })

        # 按融合分数降序排序
        fused_results.sort(key=lambda x: x["score"], reverse=True)

        logger.debug(f"混合融合: {len(fused_results)} 个文档, 向量:{len(vector_results)}, BM25:{len(bm25_results)}")

        return fused_results[:top_k]

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
