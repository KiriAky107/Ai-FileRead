"""
纯文本 (.txt) 解析器
"""
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import chardet

from .base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class TxtParser(BaseParser):
    """纯文本文档解析器"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.txt']
        self.parser_name = "txt_parser"

    def parse(
        self,
        file_path: str,
        encoding: Optional[str] = None,
        **kwargs
    ) -> ParseResult:
        """
        解析文本文件

        Args:
            file_path: 文件路径
            encoding: 指定编码，不指定则自动检测
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
            # 检测编码
            if not encoding:
                encoding = self._detect_encoding(file_path)

            # 读取文件内容
            with open(file_path, 'r', encoding=encoding) as f:
                raw_content = f.read()

            # 清理文本
            content = self._clean_text(raw_content)

            # 提取行信息
            lines = content.split('\n')

            # 估算字数
            word_count = len(content.replace('\n', '').replace(' ', ''))

            # 构建元数据
            metadata = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "file_size": path.stat().st_size,
                "encoding": encoding,
                "line_count": len(lines),
                "word_count": word_count,
                "char_count": len(content),
                "non_empty_line_count": len([l for l in lines if l.strip()])
            }

            return ParseResult(
                success=True,
                data={
                    "content": content,
                    "raw_content": raw_content,
                    "lines": lines,
                    "word_count": word_count,
                    "char_count": len(content),
                    "line_count": len(lines),
                    "structured_data": {
                        "line_count": len(lines),
                        "non_empty_line_count": metadata["non_empty_line_count"]
                    }
                },
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"解析文本文件失败: {str(e)}")
            return ParseResult(
                success=False,
                error=f"解析文本文件失败: {str(e)}"
            )

    def _detect_encoding(self, file_path: str) -> str:
        """
        自动检测文件编码

        Args:
            file_path: 文件路径

        Returns:
            检测到的编码
        """
        try:
            with open(file_path, 'rb') as f:
                raw_data = f.read()

            result = chardet.detect(raw_data)
            encoding = result.get('encoding', 'utf-8')

            # 验证编码是否有效
            if encoding:
                try:
                    raw_data.decode(encoding)
                    return encoding
                except (UnicodeDecodeError, LookupError):
                    pass

            return 'utf-8'

        except Exception as e:
            logger.warning(f"编码检测失败，使用默认编码: {str(e)}")
            return 'utf-8'

    def _clean_text(self, text: str) -> str:
        """
        清理文本内容

        - 去除多余空白字符
        - 规范化换行符
        - 去除特殊控制字符

        Args:
            text: 原始文本

        Returns:
            清理后的文本
        """
        # 规范化换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # 去除控制字符（除了换行和tab）
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

        # 将多个连续空格合并为一个
        text = re.sub(r'[ \t]+', ' ', text)

        # 将多个连续空行合并为一个
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def extract_structured_data(self, content: str) -> Dict[str, Any]:
        """
        尝试从文本中提取结构化数据

        支持提取:
        - 邮箱地址
        - URL
        - 电话号码
        - 日期
        - 金额

        Args:
            content: 文本内容

        Returns:
            结构化数据字典
        """
        data = {
            "emails": [],
            "urls": [],
            "phones": [],
            "dates": [],
            "amounts": []
        }

        # 提取邮箱
        emails = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)
        data["emails"] = list(set(emails))

        # 提取 URL
        urls = re.findall(r'https?://[^\s<>"{}|\\^`\[\]]+', content)
        data["urls"] = list(set(urls))

        # 提取电话号码 (支持多种格式)
        phone_patterns = [
            r'1[3-9]\d{9}',  # 手机号
            r'\d{3,4}-\d{7,8}',  # 固话
        ]
        phones = []
        for pattern in phone_patterns:
            phones.extend(re.findall(pattern, content))
        data["phones"] = list(set(phones))

        # 提取日期
        date_patterns = [
            r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?',
            r'\d{4}\.\d{1,2}\.\d{1,2}',
        ]
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, content))
        data["dates"] = list(set(dates))

        # 提取金额
        amount_patterns = [
            r'¥\s*\d+(?:\.\d{1,2})?',
            r'\$\s*\d+(?:\.\d{1,2})?',
            r'\d+(?:\.\d{1,2})?\s*元',
        ]
        amounts = []
        for pattern in amount_patterns:
            amounts.extend(re.findall(pattern, content))
        data["amounts"] = list(set(amounts))

        return data

    def split_into_chunks(
        self,
        content: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> List[str]:
        """
        将长文本分割成块

        用于 RAG 索引或 LLM 处理

        Args:
            content: 文本内容
            chunk_size: 每块字符数
            overlap: 块之间的重叠字符数

        Returns:
            文本块列表
        """
        if len(content) <= chunk_size:
            return [content]

        chunks = []
        start = 0

        while start < len(content):
            end = start + chunk_size
            chunk = content[start:end]

            # 尝试在句子边界分割
            if end < len(content):
                last_period = chunk.rfind('。')
                last_newline = chunk.rfind('\n')
                split_pos = max(last_period, last_newline)

                if split_pos > chunk_size // 2:
                    chunk = chunk[:split_pos + 1]
                    end = start + split_pos + 1

            chunks.append(chunk)
            start = end - overlap if end < len(content) else end

        return chunks
