"""
文件服务模块 - 处理文件存储和读取
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

from app.config import settings


class FileService:
    """文件服务类，负责文件的存储、读取和管理"""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        """确保上传目录存在"""
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_uploaded_file(
        self,
        file_content: bytes,
        filename: str,
        subfolder: Optional[str] = None
    ) -> str:
        """
        保存上传的文件

        Args:
            file_content: 文件内容字节
            filename: 原始文件名
            subfolder: 可选的子文件夹名称

        Returns:
            str: 保存后的文件路径
        """
        # 生成唯一文件名，避免覆盖
        file_ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{file_ext}"

        # 确定保存路径
        if subfolder:
            save_dir = self.upload_dir / subfolder
            save_dir.mkdir(parents=True, exist_ok=True)
        else:
            save_dir = self.upload_dir

        file_path = save_dir / unique_name

        # 写入文件
        with open(file_path, 'wb') as f:
            f.write(file_content)

        return str(file_path)

    def read_file(self, file_path: str) -> bytes:
        """
        读取文件内容

        Args:
            file_path: 文件路径

        Returns:
            bytes: 文件内容
        """
        with open(file_path, 'rb') as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        """
        删除文件

        Args:
            file_path: 文件路径

        Returns:
            bool: 是否删除成功
        """
        try:
            file = Path(file_path)
            if file.exists():
                file.unlink()
                return True
            return False
        except Exception:
            return False

    def get_file_info(self, file_path: str) -> dict:
        """
        获取文件信息

        Args:
            file_path: 文件路径

        Returns:
            dict: 文件信息
        """
        file = Path(file_path)
        if not file.exists():
            return {}

        stat = file.stat()
        return {
            "filename": file.name,
            "filepath": str(file),
            "size": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file.suffix.lower()
        }

    def get_file_size(self, file_path: str) -> int:
        """
        获取文件大小（字节）

        Args:
            file_path: 文件路径

        Returns:
            int: 文件大小，文件不存在返回 0
        """
        file = Path(file_path)
        return file.stat().st_size if file.exists() else 0


# 全局单例
file_service = FileService()
