"""
文档解析工具函数
"""
import re
from typing import List, Optional, Dict, Any


def clean_text(text: str) -> str:
    """
    清洗文本，去除多余的空白字符和特殊符号

    Args:
        text: 原始文本

    Returns:
        str: 清洗后的文本
    """
    if not text:
        return ""

    # 去除首尾空白
    text = text.strip()

    # 将多个连续的空白字符替换为单个空格
    text = re.sub(r'\s+', ' ', text)

    # 去除不可打印字符
    text = ''.join(char for char in text if char.isprintable() or char in '\n\r\t')

    return text


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 100
) -> List[str]:
    """
    将文本分块

    Args:
        text: 原始文本
        chunk_size: 每块的大小（字符数）
        overlap: 重叠区域的大小

    Returns:
        List[str]: 文本块列表
    """
    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def normalize_string(s: Any) -> str:
    """
    标准化字符串

    Args:
        s: 输入值

    Returns:
        str: 标准化后的字符串
    """
    if s is None:
        return ""
    if isinstance(s, (int, float)):
        return str(s)
    if isinstance(s, str):
        return clean_text(s)
    return str(s)


def detect_encoding(file_path: str) -> Optional[str]:
    """
    检测文件编码（简化版）

    Args:
        file_path: 文件路径

    Returns:
        Optional[str]: 编码格式，无法检测则返回 None
    """
    import chardet

    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)  # 读取前 10000 字节
            result = chardet.detect(raw_data)
            return result.get('encoding')
    except Exception:
        return None


def safe_get(d: Dict[str, Any], key: str, default: Any = None) -> Any:
    """
    安全地获取字典值

    Args:
        d: 字典
        key: 键
        default: 默认值

    Returns:
        Any: 字典值或默认值
    """
    try:
        return d.get(key, default)
    except Exception:
        return default
