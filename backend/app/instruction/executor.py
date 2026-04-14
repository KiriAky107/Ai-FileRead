"""
指令执行器模块

将自然语言指令转换为可执行操作
"""
import logging
import json
from typing import Any, Dict, List, Optional

from app.services.template_fill_service import template_fill_service
from app.services.rag_service import rag_service
from app.services.markdown_ai_service import markdown_ai_service
from app.core.database import mongodb

logger = logging.getLogger(__name__)


class InstructionExecutor:
    """指令执行器"""

    def __init__(self):
        self.intent_parser = None  # 将通过 set_intent_parser 设置

    def set_intent_parser(self, intent_parser):
        """设置意图解析器"""
        self.intent_parser = intent_parser

    async def execute(self, instruction: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行指令

        Args:
            instruction: 自然语言指令
            context: 执行上下文（包含文档信息等）

        Returns:
            执行结果
        """
        if self.intent_parser is None:
            from app.instruction.intent_parser import intent_parser
            self.intent_parser = intent_parser

        context = context or {}

        # 解析意图
        intent, params = await self.intent_parser.parse(instruction)

        # 根据意图类型执行相应操作
        if intent == "extract":
            return await self._execute_extract(params, context)
        elif intent == "fill_table":
            return await self._execute_fill_table(params, context)
        elif intent == "summarize":
            return await self._execute_summarize(params, context)
        elif intent == "question":
            return await self._execute_question(params, context)
        elif intent == "search":
            return await self._execute_search(params, context)
        elif intent == "compare":
            return await self._execute_compare(params, context)
        elif intent == "edit":
            return await self._execute_edit(params, context)
        elif intent == "transform":
            return await self._execute_transform(params, context)
        else:
            return {
                "success": False,
                "error": f"未知意图类型: {intent}",
                "message": "无法理解该指令，请尝试更明确的描述"
            }

    async def _execute_extract(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行信息提取"""
        try:
            target_fields = params.get("field_refs", [])
            doc_ids = params.get("document_refs", [])

            if not target_fields:
                return {
                    "success": False,
                    "error": "未指定要提取的字段",
                    "message": "请明确说明要提取哪些字段，如：'提取医院数量和床位数'"
                }

            # 如果指定了文档，验证文档存在
            if doc_ids and "all_docs" not in doc_ids:
                valid_docs = []
                for doc_ref in doc_ids:
                    doc_id = doc_ref.replace("doc_", "")
                    doc = await mongodb.get_document(doc_id)
                    if doc:
                        valid_docs.append(doc)
                if not valid_docs:
                    return {
                        "success": False,
                        "error": "指定的文档不存在",
                        "message": "请检查文档编号是否正确"
                    }
                context["source_docs"] = valid_docs

            # 构建字段列表
            fields = []
            for i, field_name in enumerate(target_fields):
                fields.append({
                    "name": field_name,
                    "cell": f"A{i+1}",
                    "field_type": "text",
                    "required": False
                })

            # 调用填表服务
            result = await template_fill_service.fill_template(
                template_fields=fields,
                source_doc_ids=[doc.get("_id") for doc in context.get("source_docs", [])] if context.get("source_docs") else None,
                user_hint=f"请提取字段: {', '.join(target_fields)}"
            )

            return {
                "success": True,
                "intent": "extract",
                "extracted_data": result.get("filled_data", {}),
                "fields": target_fields,
                "message": f"成功提取 {len(result.get('filled_data', {}))} 个字段"
            }

        except Exception as e:
            logger.error(f"提取执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"提取失败: {str(e)}"
            }

    async def _execute_fill_table(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行填表操作"""
        try:
            template_file = context.get("template_file")
            if not template_file:
                return {
                    "success": False,
                    "error": "未提供表格模板",
                    "message": "请先上传要填写的表格模板"
                }

            # 获取源文档
            source_docs = context.get("source_docs", [])
            source_doc_ids = [doc.get("_id") for doc in source_docs if doc.get("_id")]

            # 获取字段
            fields = context.get("template_fields", [])

            # 调用填表服务
            result = await template_fill_service.fill_template(
                template_fields=fields,
                source_doc_ids=source_doc_ids if source_doc_ids else None,
                source_file_paths=context.get("source_file_paths"),
                user_hint=params.get("user_hint"),
                template_id=template_file if isinstance(template_file, str) else None,
                template_file_type=params.get("template", {}).get("type", "xlsx")
            )

            return {
                "success": True,
                "intent": "fill_table",
                "result": result,
                "message": f"填表完成，成功填写 {len(result.get('filled_data', {}))} 个字段"
            }

        except Exception as e:
            logger.error(f"填表执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"填表失败: {str(e)}"
            }

    async def _execute_summarize(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行摘要总结"""
        try:
            docs = context.get("source_docs", [])
            if not docs:
                return {
                    "success": False,
                    "error": "没有可用的文档",
                    "message": "请先上传要总结的文档"
                }

            summaries = []
            for doc in docs[:5]:  # 最多处理5个文档
                content = doc.get("content", "")[:5000]  # 限制内容长度
                if content:
                    summaries.append({
                        "filename": doc.get("metadata", {}).get("original_filename", "未知"),
                        "content_preview": content[:500] + "..." if len(content) > 500 else content
                    })

            return {
                "success": True,
                "intent": "summarize",
                "summaries": summaries,
                "message": f"找到 {len(summaries)} 个文档可供参考"
            }

        except Exception as e:
            logger.error(f"摘要执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"摘要生成失败: {str(e)}"
            }

    async def _execute_question(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行问答"""
        try:
            question = params.get("question", "")
            if not question:
                return {
                    "success": False,
                    "error": "未提供问题",
                    "message": "请输入要回答的问题"
                }

            # 使用 RAG 检索相关文档
            docs = context.get("source_docs", [])
            rag_results = []

            for doc in docs:
                doc_id = doc.get("_id", "")
                if doc_id:
                    results = rag_service.retrieve_by_doc_id(doc_id, top_k=3)
                    rag_results.extend(results)

            # 构建上下文
            context_text = "\n\n".join([
                r.get("content", "") for r in rag_results[:5]
            ]) if rag_results else ""

            # 如果没有 RAG 结果，使用文档内容
            if not context_text:
                context_text = "\n\n".join([
                    doc.get("content", "")[:3000] for doc in docs[:3] if doc.get("content")
                ])

            return {
                "success": True,
                "intent": "question",
                "question": question,
                "context_preview": context_text[:500] + "..." if len(context_text) > 500 else context_text,
                "message": "已找到相关上下文，可进行问答"
            }

        except Exception as e:
            logger.error(f"问答执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"问答处理失败: {str(e)}"
            }

    async def _execute_search(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行搜索"""
        try:
            field_refs = params.get("field_refs", [])
            query = " ".join(field_refs) if field_refs else params.get("question", "")

            if not query:
                return {
                    "success": False,
                    "error": "未提供搜索关键词",
                    "message": "请输入要搜索的关键词"
                }

            # 使用 RAG 检索
            results = rag_service.retrieve(query, top_k=10, min_score=0.3)

            return {
                "success": True,
                "intent": "search",
                "query": query,
                "results": [
                    {
                        "content": r.get("content", "")[:200],
                        "score": r.get("score", 0),
                        "doc_id": r.get("doc_id", "")
                    }
                    for r in results[:10]
                ],
                "message": f"找到 {len(results)} 条相关结果"
            }

        except Exception as e:
            logger.error(f"搜索执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"搜索失败: {str(e)}"
            }

    async def _execute_compare(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行对比分析"""
        try:
            docs = context.get("source_docs", [])
            if len(docs) < 2:
                return {
                    "success": False,
                    "error": "对比需要至少2个文档",
                    "message": "请上传至少2个文档进行对比"
                }

            # 提取文档基本信息
            comparison = []
            for i, doc in enumerate(docs[:5]):
                comparison.append({
                    "index": i + 1,
                    "filename": doc.get("metadata", {}).get("original_filename", "未知"),
                    "doc_type": doc.get("doc_type", "未知"),
                    "content_length": len(doc.get("content", "")),
                    "has_tables": bool(doc.get("structured_data", {}).get("tables")),
                })

            return {
                "success": True,
                "intent": "compare",
                "comparison": comparison,
                "message": f"对比了 {len(comparison)} 个文档的基本信息"
            }

        except Exception as e:
            logger.error(f"对比执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"对比分析失败: {str(e)}"
            }

    async def _execute_edit(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行文档编辑操作"""
        try:
            docs = context.get("source_docs", [])
            if not docs:
                return {
                    "success": False,
                    "error": "没有可用的文档",
                    "message": "请先上传要编辑的文档"
                }

            doc = docs[0]  # 默认编辑第一个文档
            content = doc.get("content", "")
            original_filename = doc.get("metadata", {}).get("original_filename", "未知文档")

            if not content:
                return {
                    "success": False,
                    "error": "文档内容为空",
                    "message": "该文档没有可编辑的内容"
                }

            # 使用 LLM 进行文本润色/编辑
            prompt = f"""请对以下文档内容进行编辑处理。

原文内容：
{content[:8000]}

编辑要求：
- 润色表述，使其更加专业流畅
- 修正明显的语法错误
- 保持原意不变
- 只返回编辑后的内容，不要解释

请直接输出编辑后的内容："""

            messages = [
                {"role": "system", "content": "你是一个专业的文本编辑助手。请直接输出编辑后的内容。"},
                {"role": "user", "content": prompt}
            ]

            from app.services.llm_service import llm_service
            response = await llm_service.chat(messages=messages, temperature=0.3, max_tokens=8000)
            edited_content = llm_service.extract_message_content(response)

            return {
                "success": True,
                "intent": "edit",
                "edited_content": edited_content,
                "original_filename": original_filename,
                "message": "文档编辑完成，内容已返回"
            }

        except Exception as e:
            logger.error(f"编辑执行失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"编辑处理失败: {str(e)}"
            }

    async def _execute_transform(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行格式转换操作

        支持：
        - Word -> Excel
        - Excel -> Word
        - Markdown -> Word
        - Word -> Markdown
        """
        try:
            docs = context.get("source_docs", [])
            if not docs:
                return {
                    "success": False,
                    "error": "没有可用的文档",
                    "message": "请先上传要转换的文档"
                }

            # 获取目标格式
            template_info = params.get("template", {})
            target_type = template_info.get("type", "")

            if not target_type:
                # 尝试从指令中推断
                instruction = params.get("instruction", "")
                if "excel" in instruction.lower() or "xlsx" in instruction.lower():
                    target_type = "xlsx"
                elif "word" in instruction.lower() or "docx" in instruction.lower():
                    target_type = "docx"
                elif "markdown" in instruction.lower() or "md" in instruction.lower():
                    target_type = "md"

            if not target_type:
                return {
                    "success": False,
                    "error": "未指定目标格式",
                    "message": "请说明要转换成什么格式（如：转成Excel、转成Word）"
                }

            doc = docs[0]
            content = doc.get("content", "")
            structured_data = doc.get("structured_data", {})
            original_filename = doc.get("metadata", {}).get("original_filename", "未知文档")

            # 构建转换内容
            if structured_data.get("tables"):
                # 有表格数据，生成表格格式的内容
                tables = structured_data.get("tables", [])
                table_content = []
                for i, table in enumerate(tables[:3]):  # 最多处理3个表格
                    headers = table.get("headers", [])
                    rows = table.get("rows", [])[:20]  # 最多20行
                    if headers:
                        table_content.append(f"【表格 {i+1}】")
                        table_content.append(" | ".join(str(h) for h in headers))
                        table_content.append(" | ".join(["---"] * len(headers)))
                        for row in rows:
                            if isinstance(row, list):
                                table_content.append(" | ".join(str(c) for c in row))
                            elif isinstance(row, dict):
                                table_content.append(" | ".join(str(row.get(h, "")) for h in headers))
                        table_content.append("")

                if target_type == "xlsx":
                    # 生成 Excel 格式的数据（JSON）
                    excel_data = []
                    for table in tables[:1]:  # 只处理第一个表格
                        headers = table.get("headers", [])
                        rows = table.get("rows", [])[:100]
                        for row in rows:
                            if isinstance(row, list):
                                excel_data.append(dict(zip(headers, row)))
                            elif isinstance(row, dict):
                                excel_data.append(row)

                    return {
                        "success": True,
                        "intent": "transform",
                        "transform_type": "to_excel",
                        "target_format": "xlsx",
                        "excel_data": excel_data,
                        "headers": headers,
                        "message": f"已转换为 Excel 格式，包含 {len(excel_data)} 行数据"
                    }
                elif target_type in ["docx", "word"]:
                    # 生成 Word 格式的文本
                    word_content = f"# {original_filename}\n\n"
                    word_content += "\n".join(table_content)

                    return {
                        "success": True,
                        "intent": "transform",
                        "transform_type": "to_word",
                        "target_format": "docx",
                        "content": word_content,
                        "message": "已转换为 Word 格式"
                    }
                elif target_type == "md":
                    # 生成 Markdown 格式
                    md_content = f"# {original_filename}\n\n"
                    md_content += "\n".join(table_content)

                    return {
                        "success": True,
                        "intent": "transform",
                        "transform_type": "to_markdown",
                        "target_format": "md",
                        "content": md_content,
                        "message": "已转换为 Markdown 格式"
                    }

            # 无表格数据，使用纯文本内容转换
            if target_type == "xlsx":
                # 将文本内容转为 Excel 格式（每行作为一列）
                lines = [line.strip() for line in content.split("\n") if line.strip()][:100]
                excel_data = [{"行号": i+1, "内容": line} for i, line in enumerate(lines)]

                return {
                    "success": True,
                    "intent": "transform",
                    "transform_type": "to_excel",
                    "target_format": "xlsx",
                    "excel_data": excel_data,
                    "headers": ["行号", "内容"],
                    "message": f"已将文本内容转换为 Excel，包含 {len(excel_data)} 行"
                }
            elif target_type in ["docx", "word"]:
                return {
                    "success": True,
                    "intent": "transform",
                    "transform_type": "to_word",
                    "target_format": "docx",
                    "content": content,
                    "message": "文档内容已准备好，可下载为 Word 格式"
                }
            elif target_type == "md":
                # 简单的文本转 Markdown
                md_lines = []
                for line in content.split("\n"):
                    line = line.strip()
                    if line:
                        # 简单处理：如果行不长且不是列表格式，作为段落
                        if len(line) < 100 and not line.startswith(("-", "*", "1.", "2.", "3.")):
                            md_lines.append(line)
                        else:
                            md_lines.append(line)
                    else:
                        md_lines.append("")

                return {
                    "success": True,
                    "intent": "transform",
                    "transform_type": "to_markdown",
                    "target_format": "md",
                    "content": "\n".join(md_lines),
                    "message": "已转换为 Markdown 格式"
                }

            return {
                "success": False,
                "error": "不支持的目标格式",
                "message": f"暂不支持转换为 {target_type} 格式"
            }

        except Exception as e:
            logger.error(f"格式转换失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": f"格式转换失败: {str(e)}"
            }


# 全局单例
instruction_executor = InstructionExecutor()
