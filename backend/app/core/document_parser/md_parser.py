"""
Markdown 文档解析器
"""
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import markdown

from .base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class MarkdownParser(BaseParser):
    """Markdown 文档解析器"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.md', '.markdown']
        self.parser_name = "markdown_parser"

    def parse(
        self,
        file_path: str,
        **kwargs
    ) -> ParseResult:
        """
        解析 Markdown 文档

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
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            # 解析 Markdown
            md = markdown.Markdown(extensions=[
                'markdown.extensions.tables',
                'markdown.extensions.fenced_code',
                'markdown.extensions.codehilite',
                'markdown.extensions.toc',
            ])

            html_content = md.convert(raw_content)

            # 提取标题结构
            titles = self._extract_titles(raw_content)

            # 提取代码块
            code_blocks = self._extract_code_blocks(raw_content)

            # 提取表格
            tables = self._extract_tables(raw_content)

            # 提取链接和图片
            links_images = self._extract_links_images(raw_content)

            # 清理后的纯文本（去除 Markdown 语法）
            plain_text = self._strip_markdown(raw_content)

            # 构建元数据
            metadata = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "file_size": path.stat().st_size,
                "word_count": len(plain_text),
                "char_count": len(raw_content),
                "line_count": len(raw_content.splitlines()),
                "title_count": len(titles),
                "code_block_count": len(code_blocks),
                "table_count": len(tables),
                "link_count": len(links_images.get("links", [])),
                "image_count": len(links_images.get("images", [])),
            }

            return ParseResult(
                success=True,
                data={
                    "content": plain_text,
                    "raw_content": raw_content,
                    "html_content": html_content,
                    "titles": titles,
                    "code_blocks": code_blocks,
                    "tables": tables,
                    "links_images": links_images,
                    "word_count": len(plain_text),
                    "structured_data": {
                        "titles": titles,
                        "code_blocks": code_blocks,
                        "tables": tables
                    }
                },
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"解析 Markdown 文档失败: {str(e)}")
            return ParseResult(
                success=False,
                error=f"解析 Markdown 文档失败: {str(e)}"
            )

    def _extract_titles(self, content: str) -> List[Dict[str, Any]]:
        """提取标题结构"""
        import re
        titles = []

        # 匹配 # 标题
        for match in re.finditer(r'^(#{1,6})\s+(.+)$', content, re.MULTILINE):
            level = len(match.group(1))
            title_text = match.group(2).strip()
            titles.append({
                "level": level,
                "text": title_text,
                "line": content[:match.start()].count('\n') + 1
            })

        return titles

    def _extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """提取代码块"""
        import re
        code_blocks = []

        # 匹配 ```code ``` 格式
        pattern = r'```(\w*)\n(.*?)```'
        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or "text"
            code = match.group(2).strip()
            code_blocks.append({
                "language": language,
                "code": code
            })

        return code_blocks

    def _extract_tables(self, content: str) -> List[Dict[str, Any]]:
        """提取表格"""
        import re
        tables = []

        # 简单表格匹配（| col1 | col2 | 格式）
        lines = content.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # 检查是否是表格行
            if line.startswith('|') and line.endswith('|'):
                # 找到表头
                header_row = [cell.strip() for cell in line.split('|')[1:-1]]

                # 检查下一行是否是分隔符
                if i + 1 < len(lines) and re.match(r'^\|[\s\-:|]+\|$', lines[i + 1]):
                    # 跳过分隔符，读取数据行
                    data_rows = []
                    for j in range(i + 2, len(lines)):
                        row_line = lines[j].strip()
                        if not (row_line.startswith('|') and row_line.endswith('|')):
                            break
                        row_data = [cell.strip() for cell in row_line.split('|')[1:-1]]
                        data_rows.append(row_data)

                    if header_row and data_rows:
                        tables.append({
                            "headers": header_row,
                            "rows": data_rows,
                            "row_count": len(data_rows),
                            "column_count": len(header_row)
                        })
                        i = j - 1

            i += 1

        return tables

    def _extract_links_images(self, content: str) -> Dict[str, List[Dict[str, str]]]:
        """提取链接和图片"""
        import re
        result = {"links": [], "images": []}

        # 提取链接 [text](url)
        for match in re.finditer(r'\[([^\]]+)\]\(([^\)]+)\)', content):
            result["links"].append({
                "text": match.group(1),
                "url": match.group(2)
            })

        # 提取图片 ![alt](url)
        for match in re.finditer(r'!\[([^\]]*)\]\(([^\)]+)\)', content):
            result["images"].append({
                "alt": match.group(1),
                "url": match.group(2)
            })

        return result

    def _strip_markdown(self, content: str) -> str:
        """去除 Markdown 语法，获取纯文本"""
        import re

        # 去除代码块
        content = re.sub(r'```[\s\S]*?```', '', content)

        # 去除行内代码
        content = re.sub(r'`[^`]+`', '', content)

        # 去除图片
        content = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'\1', content)

        # 去除链接，保留文本
        content = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', content)

        # 去除标题标记
        content = re.sub(r'^#{1,6}\s+', '', content, flags=re.MULTILINE)

        # 去除加粗和斜体
        content = re.sub(r'\*\*([^\*]+)\*\*', r'\1', content)
        content = re.sub(r'\*([^\*]+)\*', r'\1', content)
        content = re.sub(r'__([^_]+)__', r'\1', content)
        content = re.sub(r'_([^_]+)_', r'\1', content)

        # 去除引用标记
        content = re.sub(r'^>\s+', '', content, flags=re.MULTILINE)

        # 去除列表标记
        content = re.sub(r'^[-*+]\s+', '', content, flags=re.MULTILINE)
        content = re.sub(r'^\d+\.\s+', '', content, flags=re.MULTILINE)

        # 去除水平线
        content = re.sub(r'^[-*_]{3,}$', '', content, flags=re.MULTILINE)

        # 去除表格分隔符
        content = re.sub(r'^\|[\s\-:|]+\|$', '', content, flags=re.MULTILINE)

        # 清理多余空行
        content = re.sub(r'\n{3,}', '\n\n', content)

        return content.strip()
