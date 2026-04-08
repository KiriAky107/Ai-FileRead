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
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database.mysql import Base, mysql_db

logger = logging.getLogger(__name__)
# 设置该模块的日志级别
logger.setLevel(logging.DEBUG)


class ExcelStorageService:
    """Excel 数据存储服务"""

    def __init__(self):
        self.mysql_db = mysql_db

    def _extract_sheet_names_from_xml(self, file_path: str) -> list:
        """从 Excel 文件的 XML 中提取工作表名称"""
        import zipfile
        from xml.etree import ElementTree as ET

        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                if 'xl/workbook.xml' not in z.namelist():
                    return []
                content = z.read('xl/workbook.xml')
                root = ET.fromstring(content)

                # 尝试多种命名空间
                namespaces = [
                    'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
                    'http://purl.oclc.org/ooxml/spreadsheetml/main',
                ]

                for ns_uri in namespaces:
                    ns = {'main': ns_uri}
                    sheets = root.findall('.//main:sheet', ns)
                    if sheets:
                        names = [s.get('name') for s in sheets if s.get('name')]
                        if names:
                            return names

                # 尝试通配符
                sheets = root.findall('.//{*}sheet')
                if not sheets:
                    sheets = root.findall('.//sheet')
                return [s.get('name') for s in sheets if s.get('name')]
        except Exception:
            return []

    def _read_excel_sheet(self, file_path: str, sheet_name: str = None, header_row: int = 0) -> pd.DataFrame:
        """读取 Excel 工作表，支持 pandas 无法解析的特殊 Excel 文件"""
        import zipfile
        from xml.etree import ElementTree as ET

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            if df is not None and not df.empty:
                return df
        except Exception:
            pass

        # pandas 读取失败，从 XML 直接解析
        logger.info(f"使用 XML 方式读取 Excel: {file_path}")

        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                sheet_names = self._extract_sheet_names_from_xml(file_path)
                if not sheet_names:
                    raise ValueError("无法从 Excel 文件中找到工作表")

                target_sheet = sheet_name if sheet_name and sheet_name in sheet_names else sheet_names[0]
                sheet_index = sheet_names.index(target_sheet) + 1

                shared_strings = []
                if 'xl/sharedStrings.xml' in z.namelist():
                    ss_content = z.read('xl/sharedStrings.xml')
                    ss_root = ET.fromstring(ss_content)
                    for si in ss_root.iter():
                        if si.tag.endswith('}si') or si.tag == 'si':
                            t = si.find('.//{*}t')
                            shared_strings.append(t.text if t is not None and t.text else '')

                sheet_file = f'xl/worksheets/sheet{sheet_index}.xml'
                sheet_content = z.read(sheet_file)
                root = ET.fromstring(sheet_content)

                rows_data = []
                headers = {}

                for row in root.iter():
                    if row.tag.endswith('}row') or row.tag == 'row':
                        row_idx = int(row.get('r', 0))

                        # 收集表头行
                        if row_idx == header_row + 1:
                            for cell in row:
                                if cell.tag.endswith('}c') or cell.tag == 'c':
                                    cell_ref = cell.get('r', '')
                                    col_letters = ''.join(filter(str.isalpha, cell_ref))
                                    cell_type = cell.get('t', 'n')
                                    v = cell.find('{*}v')
                                    if v is not None and v.text:
                                        if cell_type == 's':
                                            try:
                                                headers[col_letters] = shared_strings[int(v.text)]
                                            except (ValueError, IndexError):
                                                headers[col_letters] = v.text
                                        else:
                                            headers[col_letters] = v.text
                                    else:
                                        headers[col_letters] = col_letters
                            continue

                        if row_idx <= header_row + 1:
                            continue

                        row_cells = {}
                        for cell in row:
                            if cell.tag.endswith('}c') or cell.tag == 'c':
                                cell_ref = cell.get('r', '')
                                col_letters = ''.join(filter(str.isalpha, cell_ref))
                                cell_type = cell.get('t', 'n')
                                v = cell.find('{*}v')

                                if v is not None and v.text:
                                    if cell_type == 's':
                                        try:
                                            val = shared_strings[int(v.text)]
                                        except (ValueError, IndexError):
                                            val = v.text
                                    elif cell_type == 'b':
                                        val = v.text == '1'
                                    else:
                                        val = v.text
                                else:
                                    val = None
                                row_cells[col_letters] = val

                        if row_cells:
                            rows_data.append(row_cells)

                if not rows_data:
                    return pd.DataFrame()

                df = pd.DataFrame(rows_data)

                if headers:
                    df.columns = [headers.get(col, col) for col in df.columns]

                return df
        except Exception as e:
            logger.error(f"XML 解析 Excel 失败: {e}")
            raise

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
        # MySQL 支持 UTF8 编码，中文字符可以直接使用
        # 只处理非法字符（控制字符等）和首字符数字
        name = str(col_name).strip()
        # 移除控制字符
        name = re.sub(r'[\x00-\x1f\x7f]', '', name)
        # 确保以字母或中文开头
        if name and name[0].isdigit():
            name = 'col_' + name
        # 限制长度 (MySQL 字段名最多64字符)
        return name[:64]

    def _get_unique_column_name(self, col_name: str, used_names: set) -> str:
        """
        获取唯一的列名，避免重复

        Args:
            col_name: 原始列名
            used_names: 已使用的列名集合

        Returns:
            唯一的列名
        """
        sanitized = self._sanitize_column_name(col_name)
        # "id" 是 MySQL 保留名，作为主键使用
        if sanitized.lower() == "id":
            sanitized = "col_id"
        if sanitized not in used_names:
            used_names.add(sanitized)
            return sanitized

        # 添加数字后缀直到唯一
        base = sanitized if sanitized else "col"
        counter = 1
        while f"{base}_{counter}" in used_names:
            counter += 1
        unique_name = f"{base}_{counter}"
        used_names.add(unique_name)
        return unique_name

    def _infer_column_type(self, series: pd.Series) -> str:
        """
        根据数据推断列类型

        Args:
            series: pandas Series

        Returns:
            类型名称
        """
        # 移除空值进行类型检查
        non_null = series.dropna()
        if len(non_null) == 0:
            return "TEXT"

        dtype = series.dtype

        # 整数类型检查
        if pd.api.types.is_integer_dtype(dtype):
            # 检查是否所有值都能放入 INT 范围
            try:
                int_values = non_null.astype('int64')
                if int_values.min() >= -2147483648 and int_values.max() <= 2147483647:
                    return "INTEGER"
                else:
                    # 超出 INT 范围，使用 TEXT
                    return "TEXT"
            except (ValueError, OverflowError):
                return "TEXT"
        elif pd.api.types.is_float_dtype(dtype):
            # 检查是否所有值都能放入 FLOAT
            try:
                float_values = non_null.astype('float64')
                if float_values.min() >= -1e308 and float_values.max() <= 1e308:
                    return "FLOAT"
                else:
                    return "TEXT"
            except (ValueError, OverflowError):
                return "TEXT"
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
            logger.info(f"开始读取Excel文件: {file_path}")
            # 读取 Excel（使用 fallback 方式支持特殊格式文件）
            df = self._read_excel_sheet(file_path, sheet_name=sheet_name, header_row=header_row)

            logger.info(f"Excel读取完成，行数: {len(df)}, 列数: {len(df.columns)}")

            if df.empty:
                return {"success": False, "error": "Excel 文件为空"}

            # 清理列名
            df.columns = [str(c) for c in df.columns]

            # 推断列类型，并生成唯一的列名
            column_types = {}
            column_name_map = {}  # 原始列名 -> 唯一合法列名
            used_names = set()
            for col in df.columns:
                col_name = self._get_unique_column_name(col, used_names)
                col_type = self._infer_column_type(df[col])
                column_types[col] = col_type
                column_name_map[col] = col_name
                results["columns"].append({
                    "original_name": col,
                    "sanitized_name": col_name,
                    "type": col_type
                })

            # 创建表 - 使用原始 SQL 以兼容异步
            logger.info(f"正在创建MySQL表: {table_name}")
            sql_columns = ["id INT AUTO_INCREMENT PRIMARY KEY"]
            for col in df.columns:
                col_name = column_name_map[col]
                col_type = column_types.get(col, "TEXT")
                sql_type = "INT" if col_type == "INTEGER" else "FLOAT" if col_type == "FLOAT" else "DATETIME" if col_type == "DATETIME" else "TEXT"
                sql_columns.append(f"`{col_name}` {sql_type}")
            sql_columns.append("created_at DATETIME DEFAULT CURRENT_TIMESTAMP")
            sql_columns.append("updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            create_sql = text(f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(sql_columns)})")
            await self.mysql_db.execute_raw_sql(str(create_sql))
            logger.info(f"MySQL表创建完成: {table_name}")

            # 插入数据
            records = []
            for _, row in df.iterrows():
                record = {}
                for col in df.columns:
                    col_name = column_name_map[col]
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

            logger.info(f"正在插入 {len(records)} 条数据到 MySQL (使用批量插入)...")
            # 使用 pymysql 直接插入以避免 SQLAlchemy 异步问题
            import pymysql
            from app.config import settings

            connection = pymysql.connect(
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
                user=settings.MYSQL_USER,
                password=settings.MYSQL_PASSWORD,
                database=settings.MYSQL_DATABASE,
                charset=settings.MYSQL_CHARSET
            )
            try:
                columns_str = ', '.join(['`' + column_name_map[col] + '`' for col in df.columns])
                placeholders = ', '.join(['%s' for _ in df.columns])
                insert_sql = f"INSERT INTO `{table_name}` ({columns_str}) VALUES ({placeholders})"

                # 转换为元组列表 (使用映射后的列名)
                param_list = [tuple(record.get(column_name_map[col]) for col in df.columns) for record in records]

                with connection.cursor() as cursor:
                    cursor.executemany(insert_sql, param_list)
                    connection.commit()
                logger.info(f"数据插入完成: {len(records)} 条")
            finally:
                connection.close()

            results["row_count"] = len(records)
            logger.info(f"Excel 数据已存储到 MySQL 表 {table_name}，共 {len(records)} 行")

            return results

        except Exception as e:
            logger.error(f"存储 Excel 到 MySQL 失败: {str(e)}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def store_structured_data(
        self,
        table_name: str,
        data: Dict[str, Any],
        source_doc_id: str = None
    ) -> Dict[str, Any]:
        """
        将结构化数据（从非结构化文档提取的表格）存储到 MySQL

        Args:
            table_name: 表名
            data: 结构化数据，格式为:
                {
                    "columns": ["col1", "col2"],  # 列名
                    "rows": [["val1", "val2"], ["val3", "val4"]]  # 数据行
                }
            source_doc_id: 源文档 ID

        Returns:
            存储结果
        """
        results = {
            "success": True,
            "table_name": table_name,
            "row_count": 0,
            "columns": []
        }

        try:
            columns = data.get("columns", [])
            rows = data.get("rows", [])

            if not columns or not rows:
                return {"success": False, "error": "数据为空"}

            # 清理列名
            sanitized_columns = [self._sanitize_column_name(c) for c in columns]

            # 推断列类型
            column_types = {}
            for i, col in enumerate(columns):
                col_values = [row[i] for row in rows if i < len(row)]
                # 根据数据推断类型
                col_type = self._infer_type_from_values(col_values)
                column_types[col] = col_type
                results["columns"].append({
                    "original_name": col,
                    "sanitized_name": self._sanitize_column_name(col),
                    "type": col_type
                })

            # 创建表
            model_class = self._create_table_model(table_name, columns, column_types)

            # 创建表结构
            async with self.mysql_db.get_session() as session:
                model_class.__table__.create(session.bind, checkfirst=True)

            # 插入数据
            records = []
            for row in rows:
                record = {}
                for i, col in enumerate(columns):
                    if i >= len(row):
                        continue
                    col_name = self._sanitize_column_name(col)
                    value = row[i]
                    col_type = column_types.get(col, "TEXT")

                    # 处理空值
                    if value is None or str(value).strip() == '':
                        record[col_name] = None
                    elif col_type == "INTEGER":
                        try:
                            record[col_name] = int(value)
                        except (ValueError, TypeError):
                            record[col_name] = None
                    elif col_type == "FLOAT":
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
            logger.info(f"结构化数据已存储到 MySQL 表 {table_name}，共 {len(records)} 行")

            return results

        except Exception as e:
            logger.error(f"存储结构化数据到 MySQL 失败: {str(e)}")
            return {"success": False, "error": str(e)}

    def _infer_type_from_values(self, values: List[Any]) -> str:
        """
        根据值列表推断列类型

        Args:
            values: 值列表

        Returns:
            类型名称
        """
        non_null_values = [v for v in values if v is not None and str(v).strip() != '']
        if not non_null_values:
            return "TEXT"

        # 检查是否全是整数
        is_integer = all(self._is_integer(v) for v in non_null_values)
        if is_integer:
            return "INTEGER"

        # 检查是否全是浮点数
        is_float = all(self._is_float(v) for v in non_null_values)
        if is_float:
            return "FLOAT"

        return "TEXT"

    def _is_integer(self, value: Any) -> bool:
        """判断值是否可以转为整数"""
        try:
            int(value)
            return True
        except (ValueError, TypeError):
            return False

    def _is_float(self, value: Any) -> bool:
        """判断值是否可以转为浮点数"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

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
