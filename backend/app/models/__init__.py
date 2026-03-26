"""
数据模型模块

定义数据库表结构和数据模型
"""
from app.core.database.mysql import (
    Base,
    DocumentField,
    DocumentTable,
    TaskRecord,
)

__all__ = [
    "Base",
    "DocumentTable",
    "DocumentField",
    "TaskRecord",
]
