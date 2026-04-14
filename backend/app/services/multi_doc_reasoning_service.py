"""
多文档关联推理服务

跨文档信息关联和推理
"""
import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service

logger = logging.getLogger(__name__)


class MultiDocReasoningService:
    """
    多文档关联推理服务

    功能：
    1. 实体跨文档追踪 - 追踪同一实体在不同文档中的描述
    2. 关系抽取与推理 - 抽取实体间关系并进行推理
    3. 信息补全 - 根据多个文档的信息互补填充缺失数据
    4. 冲突检测 - 检测不同文档间的信息冲突
    """

    def __init__(self):
        self.llm = llm_service

    async def analyze_cross_documents(
        self,
        documents: List[Dict[str, Any]],
        query: Optional[str] = None,
        entity_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        跨文档分析

        Args:
            documents: 文档列表
            query: 查询意图（可选）
            entity_types: 要追踪的实体类型列表，如 ["机构", "人物", "地点", "数量"]

        Returns:
            跨文档分析结果
        """
        if not documents:
            return {"success": False, "error": "没有可用的文档"}

        entity_types = entity_types or ["机构", "数量", "时间", "地点"]

        try:
            # 1. 提取各文档中的实体
            entities_per_doc = await self._extract_entities_from_docs(documents, entity_types)

            # 2. 跨文档实体对齐
            aligned_entities = self._align_entities_across_docs(entities_per_doc)

            # 3. 关系抽取
            relations = await self._extract_relations(documents)

            # 4. 构建知识图谱
            knowledge_graph = self._build_knowledge_graph(aligned_entities, relations)

            # 5. 信息补全
            completed_info = await self._complete_missing_info(knowledge_graph, documents)

            # 6. 冲突检测
            conflicts = self._detect_conflicts(aligned_entities)

            return {
                "success": True,
                "entities": aligned_entities,
                "relations": relations,
                "knowledge_graph": knowledge_graph,
                "completed_info": completed_info,
                "conflicts": conflicts,
                "summary": self._generate_summary(aligned_entities, conflicts)
            }

        except Exception as e:
            logger.error(f"跨文档分析失败: {e}")
            return {"success": False, "error": str(e)}

    async def _extract_entities_from_docs(
        self,
        documents: List[Dict[str, Any]],
        entity_types: List[str]
    ) -> List[Dict[str, Any]]:
        """从各文档中提取实体"""
        entities_per_doc = []

        for idx, doc in enumerate(documents):
            doc_id = doc.get("_id", f"doc_{idx}")
            content = doc.get("content", "")[:8000]  # 限制长度

            # 使用 LLM 提取实体
            prompt = f"""从以下文档中提取指定的实体类型信息。

实体类型: {', '.join(entity_types)}

文档内容:
{content}

请按以下 JSON 格式输出（只需输出 JSON）：
{{
    "entities": [
        {{"type": "机构", "name": "实体名称", "value": "相关数值（如有）", "context": "上下文描述"}},
        ...
    ]
}}

只提取在文档中明确提到的实体，不要推测。"""

            messages = [
                {"role": "system", "content": "你是一个实体提取专家。请严格按JSON格式输出。"},
                {"role": "user", "content": prompt}
            ]

            try:
                response = await self.llm.chat(messages=messages, temperature=0.1, max_tokens=3000)
                content_response = self.llm.extract_message_content(response)

                # 解析 JSON
                import json
                import re
                cleaned = content_response.strip()
                json_match = re.search(r'\{[\s\S]*\}', cleaned)
                if json_match:
                    result = json.loads(json_match.group())
                    entities = result.get("entities", [])
                    entities_per_doc.append({
                        "doc_id": doc_id,
                        "doc_name": doc.get("metadata", {}).get("original_filename", f"文档{idx+1}"),
                        "entities": entities
                    })
                    logger.info(f"文档 {doc_id} 提取到 {len(entities)} 个实体")
            except Exception as e:
                logger.warning(f"文档 {doc_id} 实体提取失败: {e}")

        return entities_per_doc

    def _align_entities_across_docs(
        self,
        entities_per_doc: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        跨文档实体对齐

        将同一实体在不同文档中的描述进行关联
        """
        aligned: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        for doc_data in entities_per_doc:
            doc_id = doc_data["doc_id"]
            doc_name = doc_data["doc_name"]

            for entity in doc_data.get("entities", []):
                entity_name = entity.get("name", "")
                if not entity_name:
                    continue

                # 标准化实体名（去除空格和括号内容）
                normalized = self._normalize_entity_name(entity_name)

                aligned[normalized].append({
                    "original_name": entity_name,
                    "type": entity.get("type", "未知"),
                    "value": entity.get("value", ""),
                    "context": entity.get("context", ""),
                    "source_doc": doc_name,
                    "source_doc_id": doc_id
                })

        # 合并相同实体
        result = {}
        for normalized, appearances in aligned.items():
            if len(appearances) > 1:
                result[normalized] = appearances
                logger.info(f"实体对齐: {normalized} 在 {len(appearances)} 个文档中出现")

        return result

    def _normalize_entity_name(self, name: str) -> str:
        """标准化实体名称"""
        # 去除空格
        name = name.strip()
        # 去除括号内容
        name = re.sub(r'[（(].*?[）)]', '', name)
        # 去除"第X名"等
        name = re.sub(r'^第\d+[名位个]', '', name)
        return name.strip()

    async def _extract_relations(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """从文档中抽取关系"""
        relations = []

        # 合并所有文档内容
        combined_content = "\n\n".join([
            f"【{doc.get('metadata', {}).get('original_filename', f'文档{i}')}】\n{doc.get('content', '')[:3000]}"
            for i, doc in enumerate(documents)
        ])

        prompt = f"""从以下文档内容中抽取实体之间的关系。

文档内容:
{combined_content[:8000]}

请识别以下类型的关系：
- 包含关系 (A包含B)
- 隶属关系 (A隶属于B)
- 合作关系 (A与B合作)
- 对比关系 (A vs B)
- 时序关系 (A先于B发生)

请按以下 JSON 格式输出（只需输出 JSON）：
{{
    "relations": [
        {{"entity1": "实体1", "entity2": "实体2", "relation": "关系类型", "description": "关系描述"}},
        ...
    ]
}}

如果没有找到明确的关系，返回空数组。"""

        messages = [
            {"role": "system", "content": "你是一个关系抽取专家。请严格按JSON格式输出。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.llm.chat(messages=messages, temperature=0.1, max_tokens=3000)
            content_response = self.llm.extract_message_content(response)

            import json
            import re
            cleaned = content_response.strip()
            json_match = re.search(r'\{{[\s\S]*\}}', cleaned)
            if json_match:
                result = json.loads(json_match.group())
                relations = result.get("relations", [])
                logger.info(f"抽取到 {len(relations)} 个关系")
        except Exception as e:
            logger.warning(f"关系抽取失败: {e}")

        return relations

    def _build_knowledge_graph(
        self,
        aligned_entities: Dict[str, List[Dict[str, Any]]],
        relations: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """构建知识图谱"""
        nodes = []
        edges = []
        node_ids = set()

        # 添加实体节点
        for entity_name, appearances in aligned_entities.items():
            if len(appearances) < 1:
                continue

            first_appearance = appearances[0]
            node_id = f"entity_{len(nodes)}"

            # 收集该实体在所有文档中的值
            values = [a.get("value", "") for a in appearances if a.get("value")]
            primary_value = values[0] if values else ""

            nodes.append({
                "id": node_id,
                "name": entity_name,
                "type": first_appearance.get("type", "未知"),
                "value": primary_value,
                "occurrence_count": len(appearances),
                "sources": [a.get("source_doc", "") for a in appearances]
            })
            node_ids.add(entity_name)

        # 添加关系边
        for relation in relations:
            entity1 = self._normalize_entity_name(relation.get("entity1", ""))
            entity2 = self._normalize_entity_name(relation.get("entity2", ""))

            if entity1 in node_ids and entity2 in node_ids:
                edges.append({
                    "source": entity1,
                    "target": entity2,
                    "relation": relation.get("relation", "相关"),
                    "description": relation.get("description", "")
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "entity_count": len(nodes),
                "relation_count": len(edges)
            }
        }

    async def _complete_missing_info(
        self,
        knowledge_graph: Dict[str, Any],
        documents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """根据多个文档补全信息"""
        completed = []

        for node in knowledge_graph.get("nodes", []):
            if not node.get("value") and node.get("occurrence_count", 0) > 1:
                # 实体在多个文档中出现但没有数值，尝试从 RAG 检索补充
                query = f"{node['name']} 数值 数据"
                results = rag_service.retrieve(query, top_k=3, min_score=0.3)

                if results:
                    completed.append({
                        "entity": node["name"],
                        "type": node.get("type", "未知"),
                        "source": "rag_inference",
                        "context": results[0].get("content", "")[:200],
                        "confidence": results[0].get("score", 0)
                    })

        return completed

    def _detect_conflicts(
        self,
        aligned_entities: Dict[str, List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """检测不同文档间的信息冲突"""
        conflicts = []

        for entity_name, appearances in aligned_entities.items():
            if len(appearances) < 2:
                continue

            # 检查数值冲突
            values = {}
            for appearance in appearances:
                val = appearance.get("value", "")
                if val:
                    source = appearance.get("source_doc", "未知来源")
                    values[source] = val

            if len(values) > 1:
                unique_values = set(values.values())
                if len(unique_values) > 1:
                    conflicts.append({
                        "entity": entity_name,
                        "type": "value_conflict",
                        "details": values,
                        "description": f"实体 '{entity_name}' 在不同文档中有不同数值: {values}"
                    })

        return conflicts

    def _generate_summary(
        self,
        aligned_entities: Dict[str, List[Dict[str, Any]]],
        conflicts: List[Dict[str, Any]]
    ) -> str:
        """生成摘要"""
        summary_parts = []

        total_entities = sum(len(appearances) for appearances in aligned_entities.values())
        multi_doc_entities = sum(1 for appearances in aligned_entities.values() if len(appearances) > 1)

        summary_parts.append(f"跨文档分析完成：发现 {total_entities} 个实体")
        summary_parts.append(f"其中 {multi_doc_entities} 个实体在多个文档中被提及")

        if conflicts:
            summary_parts.append(f"检测到 {len(conflicts)} 个潜在冲突")

        return "; ".join(summary_parts)

    async def answer_cross_doc_question(
        self,
        question: str,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        跨文档问答

        Args:
            question: 问题
            documents: 文档列表

        Returns:
            答案结果
        """
        # 先进行跨文档分析
        analysis_result = await self.analyze_cross_documents(documents, query=question)

        # 构建上下文
        context_parts = []

        # 添加实体信息
        for entity_name, appearances in analysis_result.get("entities", {}).items():
            contexts = [f"{a.get('source_doc')}: {a.get('context', '')}" for a in appearances[:2]]
            if contexts:
                context_parts.append(f"【{entity_name}】{' | '.join(contexts)}")

        # 添加关系信息
        for relation in analysis_result.get("relations", [])[:5]:
            context_parts.append(f"【关系】{relation.get('entity1')} {relation.get('relation')} {relation.get('entity2')}: {relation.get('description', '')}")

        context_text = "\n\n".join(context_parts) if context_parts else "未找到相关实体和关系"

        # 使用 LLM 生成答案
        prompt = f"""基于以下跨文档分析结果，回答用户问题。

问题: {question}

分析结果:
{context_text}

请直接回答问题，如果分析结果中没有相关信息，请说明"根据提供的文档无法回答该问题"。"""

        messages = [
            {"role": "system", "content": "你是一个基于文档的问答助手。请根据提供的信息回答问题。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.llm.chat(messages=messages, temperature=0.2, max_tokens=2000)
            answer = self.llm.extract_message_content(response)

            return {
                "success": True,
                "question": question,
                "answer": answer,
                "supporting_entities": list(analysis_result.get("entities", {}).keys())[:10],
                "relations_count": len(analysis_result.get("relations", []))
            }
        except Exception as e:
            logger.error(f"跨文档问答失败: {e}")
            return {"success": False, "error": str(e)}


# 全局单例
multi_doc_reasoning_service = MultiDocReasoningService()
