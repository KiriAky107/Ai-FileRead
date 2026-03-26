"""
文档解析模块 - 支持多种文件格式的解析
"""
from pathlib import Path
from typing import Dict, Optional

from .base import BaseParser, ParseResult
from .xlsx_parser import XlsxParser

# 导入其他解析器 (需要先实现)
# from .docx_parser import DocxParser
# from .md_parser import MarkdownParser
# from .txt_parser import TxtParser


class ParserFactory:
    """解析器工厂，根据文件类型返回对应解析器"""

    _parsers: Dict[str, BaseParser] = {
        '.xlsx': XlsxParser(),
        '.xls': XlsxParser(),
        # '.docx': DocxParser(),   # TODO: 待实现
        # '.md': MarkdownParser(), # TODO: 待实现
        # '.txt': TxtParser(),     # TODO: 待实现
    }

    @classmethod
    def get_parser(cls, file_path: str) -> BaseParser:
        """根据文件扩展名获取解析器"""
        ext = Path(file_path).suffix.lower()
        parser = cls._parsers.get(ext)
        if not parser:
            raise ValueError(f"不支持的文件格式: {ext}，支持的格式: {list(cls._parsers.keys())}")
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


__all__ = ['BaseParser', 'ParseResult', 'XlsxParser', 'ParserFactory']
