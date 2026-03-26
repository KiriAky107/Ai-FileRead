"""
MySQL 数据库连接管理模块

提供结构化数据的存储和查询功能
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, Dict, List, Optional

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.sql import select

from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy 声明基类"""
    pass


class MySQLDB:
    """MySQL 数据库管理类"""

    def __init__(self):
        # 异步引擎 (用于 FastAPI 异步操作)
        self.async_engine = create_async_engine(
            settings.mysql_url,
            echo=settings.DEBUG,  # SQL 日志
            pool_pre_ping=True,   # 连接前检测
            pool_size=10,
            max_overflow=20,
        )

        # 异步会话工厂
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        # 同步引擎 (用于 Celery 同步任务)
        self.sync_engine = create_engine(
            settings.mysql_url.replace("mysql+pymysql", "mysql"),
            echo=settings.DEBUG,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )

        # 同步会话工厂
        self.sync_session_factory = sessionmaker(
            bind=self.sync_engine,
            autocommit=False,
            autoflush=False,
        )

    async def init_db(self):
        """初始化数据库，创建所有表"""
        try:
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("MySQL 数据库表初始化完成")
        except Exception as e:
            logger.error(f"MySQL 数据库初始化失败: {e}")
            raise

    async def close(self):
        """关闭数据库连接"""
        await self.async_engine.dispose()
        self.sync_engine.dispose()
        logger.info("MySQL 数据库连接已关闭")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """获取异步数据库会话"""
        session = self.async_session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        执行原始 SQL 查询

        Args:
            query: SQL 查询语句
            params: 查询参数

        Returns:
            查询结果列表
        """
        async with self.get_session() as session:
            result = await session.execute(select(text(query)), params or {})
            rows = result.fetchall()
            return [dict(row._mapping) for row in rows]

    async def execute_raw_sql(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        执行原始 SQL 语句 (INSERT/UPDATE/DELETE)

        Args:
            sql: SQL 语句
            params: 语句参数

        Returns:
            执行结果
        """
        async with self.get_session() as session:
            result = await session.execute(text(sql), params or {})
            await session.commit()
            return result.lastrowid if result.lastrowid else result.rowcount


# ==================== 预定义的数据模型 ====================

class DocumentTable(Base):
    """文档元数据表 - 存储已解析文档的基本信息"""
    __tablename__ = "document_tables"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_name = Column(String(255), unique=True, nullable=False, comment="表名")
    display_name = Column(String(255), comment="显示名称")
    description = Column(Text, comment="表描述")
    source_file = Column(String(512), comment="来源文件")
    column_count = Column(Integer, default=0, comment="列数")
    row_count = Column(Integer, default=0, comment="行数")
    file_size = Column(Integer, comment="文件大小(字节)")
    created_at = Column(DateTime, comment="创建时间")
    updated_at = Column(DateTime, comment="更新时间")


class DocumentField(Base):
    """文档字段表 - 存储每个表的字段信息"""
    __tablename__ = "document_fields"

    id = Column(Integer, primary_key=True, autoincrement=True)
    table_id = Column(Integer, nullable=False, comment="所属表ID")
    field_name = Column(String(255), nullable=False, comment="字段名")
    field_type = Column(String(50), comment="字段类型")
    field_description = Column(Text, comment="字段描述/语义")
    is_key_field = Column(Integer, default=0, comment="是否主键")
    is_nullable = Column(Integer, default=1, comment="是否可空")
    sample_values = Column(Text, comment="示例值(逗号分隔)")
    created_at = Column(DateTime, comment="创建时间")


class TaskRecord(Base):
    """任务记录表 - 存储异步任务信息"""
    __tablename__ = "task_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), unique=True, nullable=False, comment="Celery任务ID")
    task_type = Column(String(50), comment="任务类型")
    status = Column(String(50), default="pending", comment="任务状态")
    input_params = Column(Text, comment="输入参数JSON")
    result_data = Column(Text, comment="结果数据JSON")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime, comment="开始时间")
    completed_at = Column(DateTime, comment="完成时间")
    created_at = Column(DateTime, comment="创建时间")


# ==================== 全局单例 ====================

mysql_db = MySQLDB()
