"""
表格模板填写服务

从非结构化文档中检索信息并填写到表格模板
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.database import mongodb
from app.services.llm_service import llm_service
from app.core.document_parser import ParserFactory

logger = logging.getLogger(__name__)


@dataclass
class TemplateField:
    """模板字段"""
    cell: str  # 单元格位置，如 "A1"
    name: str  # 字段名称
    field_type: str = "text"  # 字段类型: text/number/date
    required: bool = True
    hint: str = ""  # 字段提示词


@dataclass
class SourceDocument:
    """源文档"""
    doc_id: str
    filename: str
    doc_type: str
    content: str = ""
    structured_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FillResult:
    """填写结果"""
    field: str
    value: Any
    source: str  # 来源文档
    confidence: float = 1.0  # 置信度


class TemplateFillService:
    """表格填写服务"""

    def __init__(self):
        self.llm = llm_service

    async def fill_template(
        self,
        template_fields: List[TemplateField],
        source_doc_ids: Optional[List[str]] = None,
        source_file_paths: Optional[List[str]] = None,
        user_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        填写表格模板

        Args:
            template_fields: 模板字段列表
            source_doc_ids: 源文档 MongoDB ID 列表
            source_file_paths: 源文档文件路径列表
            user_hint: 用户提示（如"请从合同文档中提取"）

        Returns:
            填写结果
        """
        filled_data = {}
        fill_details = []

        # 1. 加载源文档内容
        source_docs = await self._load_source_documents(source_doc_ids, source_file_paths)

        if not source_docs:
            logger.warning("没有找到源文档，填表结果将全部为空")

        # 2. 对每个字段进行提取
        for field in template_fields:
            try:
                # 从源文档中提取字段值
                result = await self._extract_field_value(
                    field=field,
                    source_docs=source_docs,
                    user_hint=user_hint
                )

                # 存储结果
                filled_data[field.name] = result.value
                fill_details.append({
                    "field": field.name,
                    "cell": field.cell,
                    "value": result.value,
                    "source": result.source,
                    "confidence": result.confidence
                })

                logger.info(f"字段 {field.name} 填写完成: {result.value}")

            except Exception as e:
                logger.error(f"填写字段 {field.name} 失败: {str(e)}")
                filled_data[field.name] = f"[提取失败: {str(e)}]"
                fill_details.append({
                    "field": field.name,
                    "cell": field.cell,
                    "value": f"[提取失败]",
                    "source": "error",
                    "confidence": 0.0
                })

        return {
            "success": True,
            "filled_data": filled_data,
            "fill_details": fill_details,
            "source_doc_count": len(source_docs)
        }

    async def _load_source_documents(
        self,
        source_doc_ids: Optional[List[str]] = None,
        source_file_paths: Optional[List[str]] = None
    ) -> List[SourceDocument]:
        """
        加载源文档内容

        Args:
            source_doc_ids: MongoDB 文档 ID 列表
            source_file_paths: 源文档文件路径列表

        Returns:
            源文档列表
        """
        source_docs = []

        # 1. 从 MongoDB 加载文档
        if source_doc_ids:
            for doc_id in source_doc_ids:
                try:
                    doc = await mongodb.get_document(doc_id)
                    if doc:
                        source_docs.append(SourceDocument(
                            doc_id=doc_id,
                            filename=doc.get("metadata", {}).get("original_filename", "unknown"),
                            doc_type=doc.get("doc_type", "unknown"),
                            content=doc.get("content", ""),
                            structured_data=doc.get("structured_data", {})
                        ))
                        logger.info(f"从MongoDB加载文档: {doc_id}")
                except Exception as e:
                    logger.error(f"从MongoDB加载文档失败 {doc_id}: {str(e)}")

        # 2. 从文件路径加载文档
        if source_file_paths:
            for file_path in source_file_paths:
                try:
                    parser = ParserFactory.get_parser(file_path)
                    result = parser.parse(file_path)
                    if result.success:
                        source_docs.append(SourceDocument(
                            doc_id=file_path,
                            filename=result.metadata.get("filename", file_path.split("/")[-1]),
                            doc_type=result.metadata.get("extension", "unknown").replace(".", ""),
                            content=result.data.get("content", ""),
                            structured_data=result.data.get("structured_data", {})
                        ))
                        logger.info(f"从文件加载文档: {file_path}")
                except Exception as e:
                    logger.error(f"从文件加载文档失败 {file_path}: {str(e)}")

        return source_docs

    async def _extract_field_value(
        self,
        field: TemplateField,
        source_docs: List[SourceDocument],
        user_hint: Optional[str] = None
    ) -> FillResult:
        """
        使用 LLM 从源文档中提取字段值

        Args:
            field: 字段定义
            source_docs: 源文档列表
            user_hint: 用户提示

        Returns:
            提取结果
        """
        if not source_docs:
            return FillResult(
                field=field.name,
                value="",
                source="无源文档",
                confidence=0.0
            )

        # 构建上下文文本
        context_text = self._build_context_text(source_docs, max_length=8000)

        # 构建提示词
        hint_text = field.hint if field.hint else f"请提取{field.name}的信息"
        if user_hint:
            hint_text = f"{user_hint}。{hint_text}"

        prompt = f"""你是一个专业的数据提取专家。请根据以下文档内容，提取指定字段的信息。

需要提取的字段：
- 字段名称：{field.name}
- 字段类型：{field.field_type}
- 填写提示：{hint_text}
- 是否必填：{'是' if field.required else '否'}

参考文档内容：
{context_text}

请严格按照以下 JSON 格式输出，不要添加任何解释：
{{
    "value": "提取到的值，如果没有找到则填写空字符串",
    "source": "数据来源的文档描述（如：来自xxx文档）",
    "confidence": 0.0到1.0之间的置信度，表示对提取结果的信心程度"
}}
"""

        # 调用 LLM
        messages = [
            {"role": "system", "content": "你是一个专业的数据提取助手。请严格按JSON格式输出。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=500
            )

            content = self.llm.extract_message_content(response)

            # 解析 JSON 响应
            import json
            import re

            # 尝试提取 JSON
            json_match = re.search(r'\{[\s\S]*\}', content)
            if json_match:
                result = json.loads(json_match.group())
                return FillResult(
                    field=field.name,
                    value=result.get("value", ""),
                    source=result.get("source", "LLM生成"),
                    confidence=result.get("confidence", 0.5)
                )
            else:
                # 如果无法解析，返回原始内容
                return FillResult(
                    field=field.name,
                    value=content.strip(),
                    source="直接提取",
                    confidence=0.5
                )

        except Exception as e:
            logger.error(f"LLM 提取失败: {str(e)}")
            return FillResult(
                field=field.name,
                value="",
                source=f"提取失败: {str(e)}",
                confidence=0.0
            )

    def _build_context_text(self, source_docs: List[SourceDocument], max_length: int = 8000) -> str:
        """
        构建上下文文本

        Args:
            source_docs: 源文档列表
            max_length: 最大字符数

        Returns:
            上下文文本
        """
        contexts = []
        total_length = 0

        for doc in source_docs:
            # 优先使用结构化数据（表格），其次使用文本内容
            doc_content = ""

            if doc.structured_data and doc.structured_data.get("tables"):
                # 如果有表格数据，优先使用
                tables = doc.structured_data.get("tables", [])
                for table in tables:
                    if isinstance(table, dict):
                        rows = table.get("rows", [])
                        if rows:
                            doc_content += f"\n【文档: {doc.filename} 表格数据】\n"
                            for row in rows[:20]:  # 限制每表最多20行
                                if isinstance(row, list):
                                    doc_content += " | ".join(str(cell) for cell in row) + "\n"
                                elif isinstance(row, dict):
                                    doc_content += " | ".join(str(v) for v in row.values()) + "\n"
            elif doc.content:
                doc_content = doc.content[:5000]  # 限制文本长度

            if doc_content:
                doc_context = f"【文档: {doc.filename} ({doc.doc_type})】\n{doc_content}"
                if total_length + len(doc_context) <= max_length:
                    contexts.append(doc_context)
                    total_length += len(doc_context)
                else:
                    # 如果超出长度，截断
                    remaining = max_length - total_length
                    if remaining > 100:
                        contexts.append(doc_context[:remaining])
                    break

        return "\n\n".join(contexts) if contexts else "（源文档内容为空）"

    async def get_template_fields_from_file(
        self,
        file_path: str,
        file_type: str = "xlsx"
    ) -> List[TemplateField]:
        """
        从模板文件提取字段定义

        Args:
            file_path: 模板文件路径
            file_type: 文件类型 (xlsx/xls/docx)

        Returns:
            字段列表
        """
        fields = []

        try:
            if file_type in ["xlsx", "xls"]:
                fields = await self._get_template_fields_from_excel(file_path)
            elif file_type == "docx":
                fields = await self._get_template_fields_from_docx(file_path)

        except Exception as e:
            logger.error(f"提取模板字段失败: {str(e)}")

        return fields

    async def _get_template_fields_from_excel(self, file_path: str) -> List[TemplateField]:
        """从 Excel 模板提取字段"""
        fields = []

        try:
            import pandas as pd
            df = pd.read_excel(file_path, nrows=5)

            for idx, col in enumerate(df.columns):
                cell = self._column_to_cell(idx)
                col_str = str(col)

                fields.append(TemplateField(
                    cell=cell,
                    name=col_str,
                    field_type=self._infer_field_type_from_value(df[col].iloc[0] if len(df) > 0 else ""),
                    required=True,
                    hint=""
                ))

        except Exception as e:
            logger.error(f"从Excel提取字段失败: {str(e)}")

        return fields

    async def _get_template_fields_from_docx(self, file_path: str) -> List[TemplateField]:
        """从 Word 模板提取字段"""
        fields = []

        try:
            from docx import Document

            doc = Document(file_path)

            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    cells = [cell.text.strip() for cell in row.cells]

                    # 假设第一列是字段名
                    if cells and cells[0]:
                        field_name = cells[0]
                        hint = cells[1] if len(cells) > 1 else ""

                        # 跳过空行或标题行
                        if field_name and field_name not in ["", "字段名", "名称", "项目"]:
                            fields.append(TemplateField(
                                cell=f"T{table_idx}R{row_idx}",
                                name=field_name,
                                field_type=self._infer_field_type_from_hint(hint),
                                required=True,
                                hint=hint
                            ))

        except Exception as e:
            logger.error(f"从Word提取字段失败: {str(e)}")

        return fields

    def _infer_field_type_from_hint(self, hint: str) -> str:
        """从提示词推断字段类型"""
        hint_lower = hint.lower()

        date_keywords = ["年", "月", "日", "日期", "时间", "出生"]
        if any(kw in hint for kw in date_keywords):
            return "date"

        number_keywords = ["数量", "金额", "人数", "面积", "增长", "比率", "%", "率", "总计", "合计"]
        if any(kw in hint_lower for kw in number_keywords):
            return "number"

        return "text"

    def _infer_field_type_from_value(self, value: Any) -> str:
        """从示例值推断字段类型"""
        if value is None or value == "":
            return "text"

        value_str = str(value)

        # 检查日期模式
        import re
        if re.search(r'\d{4}[年/-]\d{1,2}[月/-]\d{1,2}', value_str):
            return "date"

        # 检查数值
        try:
            float(value_str.replace(',', '').replace('%', ''))
            return "number"
        except ValueError:
            pass

        return "text"

    def _column_to_cell(self, col_idx: int) -> str:
        """将列索引转换为单元格列名 (0 -> A, 1 -> B, ...)"""
        result = ""
        while col_idx >= 0:
            result = chr(65 + (col_idx % 26)) + result
            col_idx = col_idx // 26 - 1
        return result


# ==================== 全局单例 ====================

template_fill_service = TemplateFillService()
