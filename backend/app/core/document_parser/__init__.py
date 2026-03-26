"""
文档解析模块 - 支持多种文件格式的解析
"""
from pathlib import Path
from typing import Dict

from .base import BaseParser, ParseResult
from .xlsx_parser import XlsxParser
from .docx_parser import DocxParser
from .md_parser import MarkdownParser
from .txt_parser import TxtParser


class ParserFactory:
    """解析器工厂，根据文件类型返回对应解析器"""

    _parsers: Dict[str, BaseParser] = {
        # Excel
        '.xlsx': XlsxParser(),
        '.xls': XlsxParser(),
        # Word
        '.docx': DocxParser(),
        # Markdown
        '.md': MarkdownParser(),
        '.markdown': MarkdownParser(),
        # 文本
        '.txt': TxtParser(),
    }

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        """根据文件扩展名获取解析器"""
        ext = Path(file_path).suffix.lower()
        parser = cls._parsers.get(ext)
        if not parser:
            supported = list(cls._parsers.keys())
            raise ValueError(f"不支持的文件格式: {ext}，支持的格式: {supported}")
        return parser

    @classmethod
    def parse(cls, file_path: str, **kwargs) -> ParseResult:
        """统一解析接口"""
        parser = cls.get_parser(file_path)
        return parser.parse(file_path, **kwargs)

    @classmethod
    def register_parser(cls, ext: str, parser: BaseParser):
        """注册新的解析器"""
        cls._parsers[ext.lower()] = parser

    @classmethod
    def get_supported_extensions(cls) -> list:
        """获取所有支持的扩展名"""
        return list(cls._parsers.keys())


__all__ = [
    'BaseParser',
    'ParseResult',
    'ParserFactory',
    'XlsxParser',
    'DocxParser',
    'MarkdownParser',
    'TxtParser',
]
