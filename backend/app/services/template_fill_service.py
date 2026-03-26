"""
表格模板填写服务

从非结构化文档中检索信息并填写到表格模板
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.database import mongodb
from app.services.rag_service import rag_service
from app.services.llm_service import llm_service
from app.services.excel_storage_service import excel_storage_service

logger = logging.getLogger(__name__)


@dataclass
class TemplateField:
    """模板字段"""
    cell: str  # 单元格位置，如 "A1"
    name: str  # 字段名称
    field_type: str = "text"  # 字段类型: text/number/date
    required: bool = True


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
        self.rag = rag_service

    async def fill_template(
        self,
        template_fields: List[TemplateField],
        source_doc_ids: Optional[List[str]] = None,
        user_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        填写表格模板

        Args:
            template_fields: 模板字段列表
            source_doc_ids: 源文档ID列表，不指定则从所有文档检索
            user_hint: 用户提示（如"请从合同文档中提取"）

        Returns:
            填写结果
        """
        filled_data = {}
        fill_details = []

        for field in template_fields:
            try:
                # 1. 从 RAG 检索相关上下文
                rag_results = await self._retrieve_context(field.name, user_hint)

                if not rag_results:
                    # 如果没有检索到结果，尝试直接询问 LLM
                    result = FillResult(
                        field=field.name,
                        value="",
                        source="未找到相关数据",
                        confidence=0.0
                    )
                else:
                    # 2. 构建 Prompt 让 LLM 提取信息
                    result = await self._extract_field_value(
                        field=field,
                        rag_context=rag_results,
                        user_hint=user_hint
                    )

                # 3. 存储结果
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
            "fill_details": fill_details
        }

    async def _retrieve_context(
        self,
        field_name: str,
        user_hint: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        从 RAG 检索相关上下文

        Args:
            field_name: 字段名称
            user_hint: 用户提示

        Returns:
            检索结果列表
        """
        # 构建查询文本
        query = field_name
        if user_hint:
            query = f"{user_hint} {field_name}"

        # 检索相关文档片段
        results = self.rag.retrieve(query=query, top_k=5)

        return results

    async def _extract_field_value(
        self,
        field: TemplateField,
        rag_context: List[Dict[str, Any]],
        user_hint: Optional[str] = None
    ) -> FillResult:
        """
        使用 LLM 从上下文中提取字段值

        Args:
            field: 字段定义
            rag_context: RAG 检索到的上下文
            user_hint: 用户提示

        Returns:
            提取结果
        """
        # 构建上下文文本
        context_text = "\n\n".join([
            f"【文档 {i+1}】\n{doc['content']}"
            for i, doc in enumerate(rag_context)
        ])

        # 构建 Prompt
        prompt = f"""你是一个数据提取专家。请根据以下文档内容，提取指定字段的信息。

需要提取的字段：
- 字段名称：{field.name}
- 字段类型：{field.field_type}
- 是否必填：{'是' if field.required else '否'}

{'用户提示：' + user_hint if user_hint else ''}

参考文档内容：
{context_text}

请严格按照以下 JSON 格式输出，不要添加任何解释：
{{
    "value": "提取到的值，如果没有找到则填写空字符串",
    "source": "数据来源的文档描述",
    "confidence": 0.0到1.0之间的置信度
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

    async def get_template_fields_from_file(
        self,
        file_path: str,
        file_type: str = "xlsx"
    ) -> List[TemplateField]:
        """
        从模板文件提取字段定义

        Args:
            file_path: 模板文件路径
            file_type: 文件类型

        Returns:
            字段列表
        """
        fields = []

        try:
            if file_type in ["xlsx", "xls"]:
                # 从 Excel 读取表头
                import pandas as pd
                df = pd.read_excel(file_path, nrows=5)

                for idx, col in enumerate(df.columns):
                    # 获取单元格位置 (A, B, C, ...)
                    cell = self._column_to_cell(idx)

                    fields.append(TemplateField(
                        cell=cell,
                        name=str(col),
                        field_type=self._infer_field_type(df[col]),
                        required=True
                    ))

            elif file_type == "docx":
                # 从 Word 表格读取
                from docx import Document
                doc = Document(file_path)

                for table_idx, table in enumerate(doc.tables):
                    for row_idx, row in enumerate(table.rows):
                        for col_idx, cell in enumerate(row.cells):
                            cell_text = cell.text.strip()
                            if cell_text:
                                fields.append(TemplateField(
                                    cell=self._column_to_cell(col_idx),
                                    name=cell_text,
                                    field_type="text",
                                    required=True
                                ))

        except Exception as e:
            logger.error(f"提取模板字段失败: {str(e)}")

        return fields

    def _column_to_cell(self, col_idx: int) -> str:
        """将列索引转换为单元格列名 (0 -> A, 1 -> B, ...)"""
        result = ""
        while col_idx >= 0:
            result = chr(65 + (col_idx % 26)) + result
            col_idx = col_idx // 26 - 1
        return result

    def _infer_field_type(self, series) -> str:
        """推断字段类型"""
        import pandas as pd

        if pd.api.types.is_numeric_dtype(series):
            return "number"
        elif pd.api.types.is_datetime64_any_dtype(series):
            return "date"
        else:
            return "text"


# ==================== 全局单例 ====================

template_fill_service = TemplateFillService()
