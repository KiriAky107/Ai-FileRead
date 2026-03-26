"""
Excel 存储服务

将 Excel 数据转换为 MySQL 表结构并存储
"""
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    inspect,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.mysql import Base, mysql_db

logger = logging.getLogger(__name__)


class ExcelStorageService:
    """Excel 数据存储服务"""

    def __init__(self):
        self.mysql_db = mysql_db

    def _sanitize_table_name(self, filename: str) -> str:
        """
        将文件名转换为合法的表名

        Args:
            filename: 原始文件名

        Returns:
            合法的表名
        """
        # 移除扩展名
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename

        # 只保留字母、数字、下划线
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)

        # 确保以字母开头
        if name and name[0].isdigit():
            name = 't_' + name

        # 限制长度
        return name[:50]

    def _sanitize_column_name(self, col_name: str) -> str:
        """
        将列名转换为合法的字段名

        Args:
            col_name: 原始列名

        Returns:
            合法的字段名
        """
        # 只保留字母、数字、下划线
        name = re.sub(r'[^a-zA-Z0-9_]', '_', str(col_name))

        # 确保以字母开头
        if name and name[0].isdigit():
            name = 'col_' + name

        # 限制长度
        return name[:50]

    def _infer_column_type(self, series: pd.Series) -> str:
        """
        根据数据推断列类型

        Args:
            series: pandas Series

        Returns:
            类型名称
        """
        dtype = series.dtype

        if pd.api.types.is_integer_dtype(dtype):
            return "INTEGER"
        elif pd.api.types.is_float_dtype(dtype):
            return "FLOAT"
        elif pd.api.types.is_datetime64_any_dtype(dtype):
            return "DATETIME"
        elif pd.api.types.is_bool_dtype(dtype):
            return "BOOLEAN"
        else:
            return "TEXT"

    def _create_table_model(
        self,
        table_name: str,
        columns: List[str],
        column_types: Dict[str, str]
    ) -> type:
        """
        动态创建 SQLAlchemy 模型类

        Args:
            table_name: 表名
            columns: 列名列表
            column_types: 列类型字典

        Returns:
            SQLAlchemy 模型类
        """
        # 创建属性字典
        attrs = {
            '__tablename__': table_name,
            '__table_args__': {'extend_existing': True},
        }

        # 添加主键列
        attrs['id'] = Column(Integer, primary_key=True, autoincrement=True)

        # 添加数据列
        for col in columns:
            col_name = self._sanitize_column_name(col)
            col_type = column_types.get(col, "TEXT")

            if col_type == "INTEGER":
                attrs[col_name] = Column(Integer, nullable=True)
            elif col_type == "FLOAT":
                attrs[col_name] = Column(Float, nullable=True)
            elif col_type == "DATETIME":
                attrs[col_name] = Column(DateTime, nullable=True)
            elif col_type == "BOOLEAN":
                attrs[col_name] = Column(Integer, nullable=True)  # MySQL 没有原生 BOOLEAN
            else:
                attrs[col_name] = Column(Text, nullable=True)

        # 添加元数据列
        attrs['created_at'] = Column(DateTime, default=datetime.utcnow)
        attrs['updated_at'] = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

        # 创建类
        return type(table_name, (Base,), attrs)

    async def store_excel(
        self,
        file_path: str,
        filename: str,
        sheet_name: Optional[str] = None,
        header_row: int = 0
    ) -> Dict[str, Any]:
        """
        将 Excel 文件存储到 MySQL

        Args:
            file_path: Excel 文件路径
            filename: 原始文件名
            sheet_name: 工作表名称
            header_row: 表头行号

        Returns:
            存储结果
        """
        table_name = self._sanitize_table_name(filename)
        results = {
            "success": True,
            "table_name": table_name,
            "row_count": 0,
            "columns": []
        }

        try:
            # 读取 Excel
            if sheet_name:
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            else:
                df = pd.read_excel(file_path, header=header_row)

            if df.empty:
                return {"success": False, "error": "Excel 文件为空"}

            # 清理列名
            df.columns = [str(c) for c in df.columns]

            # 推断列类型
            column_types = {}
            for col in df.columns:
                col_name = self._sanitize_column_name(col)
                col_type = self._infer_column_type(df[col])
                column_types[col] = col_type
                results["columns"].append({
                    "original_name": col,
                    "sanitized_name": col_name,
                    "type": col_type
                })

            # 创建表
            model_class = self._create_table_model(table_name, df.columns, column_types)

            # 创建表结构
            async with self.mysql_db.get_session() as session:
                model_class.__table__.create(session.bind, checkfirst=True)

            # 插入数据
            records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    col_name = self._sanitize_column_name(col)
                    value = row[col]

                    # 处理 NaN 值
                    if pd.isna(value):
                        record[col_name] = None
                    elif column_types[col] == "INTEGER":
                        try:
                            record[col_name] = int(value)
                        except (ValueError, TypeError):
                            record[col_name] = None
                    elif column_types[col] == "FLOAT":
                        try:
                            record[col_name] = float(value)
                        except (ValueError, TypeError):
                            record[col_name] = None
                    else:
                        record[col_name] = str(value)

                records.append(record)

            # 批量插入
            async with self.mysql_db.get_session() as session:
                for record in records:
                    session.add(model_class(**record))
                await session.commit()

            results["row_count"] = len(records)
            logger.info(f"Excel 数据已存储到 MySQL 表 {table_name}，共 {len(records)} 行")

            return results

        except Exception as e:
            logger.error(f"存储 Excel 到 MySQL 失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def query_table(
        self,
        table_name: str,
        columns: Optional[List[str]] = None,
        where: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        查询 MySQL 表数据

        Args:
            table_name: 表名
            columns: 要查询的列
            where: WHERE 条件
            limit: 限制返回行数

        Returns:
            查询结果
        """
        try:
            # 构建查询
            sql = f"SELECT * FROM `{table_name}`"
            if where:
                sql += f" WHERE {where}"
            sql += f" LIMIT {limit}"

            results = await self.mysql_db.execute_query(sql)
            return results

        except Exception as e:
            logger.error(f"查询表失败: {str(e)}")
            return []

    async def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """
        获取表结构信息

        Args:
            table_name: 表名

        Returns:
            表结构信息
        """
        try:
            sql = f"""
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_KEY, COLUMN_COMMENT
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}'
                ORDER BY ORDINAL_POSITION
            """
            results = await self.mysql_db.execute_query(sql)
            return results

        except Exception as e:
            logger.error(f"获取表结构失败: {str(e)}")
            return None

    async def delete_table(self, table_name: str) -> bool:
        """
        删除表

        Args:
            table_name: 表名

        Returns:
            是否成功
        """
        try:
            # 安全检查：表名必须包含下划线（避免删除系统表）
            if '_' not in table_name and not table_name.startswith('t_'):
                raise ValueError("不允许删除此表")

            sql = f"DROP TABLE IF EXISTS `{table_name}`"
            await self.mysql_db.execute_raw_sql(sql)
            logger.info(f"表 {table_name} 已删除")
            return True

        except Exception as e:
            logger.error(f"删除表失败: {str(e)}")
            return False

    async def list_tables(self) -> List[str]:
        """
        列出所有用户表

        Returns:
            表名列表
        """
        try:
            sql = """
                SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'
            """
            results = await self.mysql_db.execute_query(sql)
            return [r['TABLE_NAME'] for r in results]

        except Exception as e:
            logger.error(f"列出表失败: {str(e)}")
            return []


# ==================== 全局单例 ====================

excel_storage_service = ExcelStorageService()
