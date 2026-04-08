"""
Word 文档 (.docx) 解析器
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from docx import Document

from .base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class DocxParser(BaseParser):
    """Word 文档解析器"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.docx']
        self.parser_name = "docx_parser"

    def parse(
        self,
        file_path: str,
        **kwargs
    ) -> ParseResult:
        """
        解析 Word 文档

        Args:
            file_path: 文件路径
            **kwargs: 其他参数

        Returns:
            ParseResult: 解析结果
        """
        path = Path(file_path)

        # 检查文件是否存在
        if not path.exists():
            return ParseResult(
                success=False,
                error=f"文件不存在: {file_path}"
            )

        # 检查文件扩展名
        if path.suffix.lower() not in self.supported_extensions:
            return ParseResult(
                success=False,
                error=f"不支持的文件类型: {path.suffix}"
            )

        try:
            # 读取 Word 文档
            doc = Document(file_path)

            # 提取文本内容
            paragraphs = []
            for para in doc.paragraphs:
                if para.text.strip():
                    paragraphs.append(para.text)

            # 提取表格内容
            tables_data = []
            for i, table in enumerate(doc.tables):
                table_rows = []
                for row in table.rows:
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_rows.append(row_data)

                if table_rows:
                    tables_data.append({
                        "table_index": i,
                        "rows": table_rows,
                        "row_count": len(table_rows),
                        "column_count": len(table_rows[0]) if table_rows else 0
                    })

            # 合并所有文本
            full_text = "\n".join(paragraphs)

            # 构建元数据
            metadata = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "file_size": path.stat().st_size,
                "paragraph_count": len(paragraphs),
                "table_count": len(tables_data),
                "word_count": len(full_text),
                "char_count": len(full_text.replace("\n", "")),
                "has_tables": len(tables_data) > 0
            }

            # 返回结果
            return ParseResult(
                success=True,
                data={
                    "content": full_text,
                    "paragraphs": paragraphs,
                    "tables": tables_data,
                    "word_count": len(full_text),
                    "structured_data": {
                        "paragraphs": paragraphs,
                        "tables": tables_data
                    }
                },
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"解析 Word 文档失败: {str(e)}")
            return ParseResult(
                success=False,
                error=f"解析 Word 文档失败: {str(e)}"
            )

    def extract_key_sentences(self, text: str, max_sentences: int = 10) -> List[str]:
        """
        从文本中提取关键句子

        Args:
            text: 文本内容
            max_sentences: 最大句子数

        Returns:
            关键句子列表
        """
        # 简单实现：按句号分割，取前N个句子
        sentences = [s.strip() for s in text.split("。") if s.strip()]
        return sentences[:max_sentences]

    def extract_structured_fields(self, text: str) -> Dict[str, Any]:
        """
        尝试提取结构化字段

        针对合同、简历等有固定格式的文档

        Args:
            text: 文本内容

        Returns:
            提取的字段字典
        """
        fields = {}

        # 常见字段模式
        patterns = {
            "姓名": r"姓名[：:]\s*(\S+)",
            "电话": r"电话[：:]\s*(\d{11}|\d{3}-\d{8})",
            "邮箱": r"邮箱[：:]\s*(\S+@\S+)",
            "地址": r"地址[：:]\s*(.+?)(?:\n|$)",
            "金额": r"金额[：:]\s*(\d+(?:\.\d+)?)",
            "日期": r"日期[：:]\s*(\d{4}[年/-]\d{1,2}[月/-]\d{1,2})",
        }

        import re
        for field_name, pattern in patterns.items():
            match = re.search(pattern, text)
            if match:
                fields[field_name] = match.group(1)

        return fields

    def parse_tables_for_template(
        self,
        file_path: str
    ) -> Dict[str, Any]:
        """
        解析 Word 文档中的表格，提取模板字段

        专门用于比赛场景：解析表格模板，识别需要填写的字段

        Args:
            file_path: Word 文件路径

        Returns:
            包含表格字段信息的字典
        """
        from docx import Document
        from docx.table import Table
        from docx.oxml.ns import qn

        doc = Document(file_path)

        template_info = {
            "tables": [],
            "fields": [],
            "field_count": 0
        }

        for table_idx, table in enumerate(doc.tables):
            table_info = {
                "table_index": table_idx,
                "rows": [],
                "headers": [],
                "data_rows": [],
                "field_hints": {}  # 字段名称 -> 提示词/描述
            }

            # 提取表头（第一行）
            if table.rows:
                header_cells = [cell.text.strip() for cell in table.rows[0].cells]
                table_info["headers"] = header_cells

                # 提取数据行
                for row_idx, row in enumerate(table.rows[1:], 1):
                    row_data = [cell.text.strip() for cell in row.cells]
                    table_info["data_rows"].append(row_data)
                    table_info["rows"].append({
                        "row_index": row_idx,
                        "cells": row_data
                    })

                # 尝试从第二列/第三列提取提示词
                # 比赛模板通常格式为：字段名 | 提示词 | 填写值
                if len(table.rows[0].cells) >= 2:
                    for row_idx, row in enumerate(table.rows[1:], 1):
                        cells = [cell.text.strip() for cell in row.cells]
                        if len(cells) >= 2 and cells[0]:
                            # 第一列是字段名
                            field_name = cells[0]
                            # 第二列可能是提示词或描述
                            hint = cells[1] if len(cells) > 1 else ""
                            table_info["field_hints"][field_name] = hint

                            template_info["fields"].append({
                                "table_index": table_idx,
                                "row_index": row_idx,
                                "field_name": field_name,
                                "hint": hint,
                                "expected_value": cells[2] if len(cells) > 2 else ""
                            })

            template_info["tables"].append(table_info)

        template_info["field_count"] = len(template_info["fields"])
        return template_info

    def extract_template_fields_from_docx(
        self,
        file_path: str
    ) -> List[Dict[str, Any]]:
        """
        从 Word 文档中提取模板字段定义

        适用于比赛评分表格：表格第一列是字段名，第二列是提示词/填写示例

        Args:
            file_path: Word 文件路径

        Returns:
            字段定义列表
        """
        template_info = self.parse_tables_for_template(file_path)

        fields = []
        for field in template_info["fields"]:
            fields.append({
                "cell": f"T{field['table_index']}R{field['row_index']}",  # TableXRowY 格式
                "name": field["field_name"],
                "hint": field["hint"],
                "table_index": field["table_index"],
                "row_index": field["row_index"],
                "field_type": self._infer_field_type_from_hint(field["hint"]),
                "required": True
            })

        return fields

    def _infer_field_type_from_hint(self, hint: str) -> str:
        """
        从提示词推断字段类型

        Args:
            hint: 字段提示词

        Returns:
            字段类型 (text/number/date)
        """
        hint_lower = hint.lower()

        # 日期关键词
        date_keywords = ["年", "月", "日", "日期", "时间", "出生"]
        if any(kw in hint for kw in date_keywords):
            return "date"

        # 数字关键词
        number_keywords = ["数量", "金额", "人数", "面积", "增长", "比率", "%", "率"]
        if any(kw in hint_lower for kw in number_keywords):
            return "number"

        return "text"
