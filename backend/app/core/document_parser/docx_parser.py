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
