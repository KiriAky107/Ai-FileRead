"""
解析器基类 - 定义所有解析器的通用接口
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class ParseResult:
    """解析结果类"""

    def __init__(
        self,
        success: bool,
        data: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "metadata": self.metadata
        }


class BaseParser(ABC):
    """文档解析器基类"""

    def __init__(self):
        self.supported_extensions: List[str] = []
        self.parser_name: str = "base_parser"

    @abstractmethod
    def parse(self, file_path: str, **kwargs) -> ParseResult:
        """
        解析文件

        Args:
            file_path: 文件路径
            **kwargs: 其他解析参数

        Returns:
            ParseResult: 解析结果
        """
        pass

    def can_parse(self, file_path: str) -> bool:
        """
        检查是否可以解析该文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否可以解析
        """
        ext = Path(file_path).suffix.lower()
        return ext in self.supported_extensions

    def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """
        获取文件基本信息

        Args:
            file_path: 文件路径

        Returns:
            Dict[str, Any]: 文件信息
        """
        path = Path(file_path)
        if not path.exists():
            return {"error": "File not found"}

        return {
            "filename": path.name,
            "extension": path.suffix.lower(),
            "size": path.stat().st_size,
            "parser": self.parser_name
        }
