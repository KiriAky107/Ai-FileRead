"""
表结构 RAG 索引服务

AI 自动生成表字段的语义描述，并建立向量索引
"""
import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from app.services.llm_service import llm_service
from app.services.rag_service import rag_service
from app.services.excel_storage_service import excel_storage_service
from app.core.database.mysql import mysql_db

logger = logging.getLogger(__name__)


class TableRAGService:
    """
    表结构 RAG 索引服务

    核心功能：
    1. AI 根据表头和数据生成字段语义描述
    2. 将字段描述存入向量数据库 (RAG)
    3. 支持自然语言查询表字段
    """

    def __init__(self):
        self.llm = llm_service
        self.rag = rag_service
        self.excel_storage = excel_storage_service

    async def generate_field_description(
        self,
        table_name: str,
        field_name: str,
        sample_values: List[Any],
        all_fields: Dict[str, List[Any]] = None
    ) -> str:
        """
        使用 AI 生成字段的语义描述

        Args:
            table_name: 表名
            field_name: 字段名
            sample_values: 字段示例值 (前10个)
            all_fields: 其他字段的示例值，用于上下文理解

        Returns:
            字段的语义描述
        """
        # 构建 Prompt
        context = ""
        if all_fields:
            context = "\n其他字段示例：\n"
            for fname, values in all_fields.items():
                if fname != field_name and values:
                    context += f"- {fname}: {', '.join([str(v) for v in values[:3]])}\n"

        prompt = f"""你是一个数据语义分析专家。请根据字段名和示例值，推断该字段的语义含义。

表名：{table_name}
字段名：{field_name}
示例值：{', '.join([str(v) for v in sample_values[:10] if v is not None])}
{context}

请生成一段简洁的字段语义描述（不超过50字），说明：
1. 该字段代表什么含义
2. 数据格式或单位（如果有）
3. 可能的业务用途

只输出描述文字，不要其他内容。"""

        try:
            messages = [
                {"role": "system", "content": "你是一个专业的数据分析师。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=200
            )

            description = self.llm.extract_message_content(response)
            return description.strip()

        except Exception as e:
            logger.error(f"生成字段描述失败: {str(e)}")
            return f"{field_name}: 数据字段"

    async def build_table_rag_index(
        self,
        file_path: str,
        filename: str,
        sheet_name: Optional[str] = None,
        header_row: int = 0,
        sample_size: int = 10
    ) -> Dict[str, Any]:
        """
        为 Excel 表构建完整的 RAG 索引

        流程：
        1. 读取 Excel 获取字段信息
        2. AI 生成每个字段的语义描述
        3. 将字段描述存入向量数据库

        Args:
            file_path: Excel 文件路径
            filename: 原始文件名
            sheet_name: 工作表名称
            header_row: 表头行号
            sample_size: 每个字段采样的数据条数

        Returns:
            索引构建结果
        """
        results = {
            "success": True,
            "table_name": "",
            "field_count": 0,
            "indexed_fields": [],
            "errors": []
        }

        try:
            # 1. 先检查 Excel 文件是否有效
            logger.info(f"正在检查Excel文件: {file_path}")
            try:
                xls_file = pd.ExcelFile(file_path)
                sheet_names = xls_file.sheet_names
                logger.info(f"Excel文件工作表: {sheet_names}")
                if not sheet_names:
                    return {"success": False, "error": "Excel 文件没有工作表"}
            except Exception as e:
                logger.error(f"读取Excel文件失败: {file_path}, error: {e}")
                return {"success": False, "error": f"无法读取Excel文件: {str(e)}"}

            # 2. 读取 Excel
            if sheet_name:
                # 验证指定的sheet_name是否存在
                if sheet_name not in sheet_names:
                    logger.warning(f"指定的工作表 '{sheet_name}' 不存在，使用第一个工作表: {sheet_names[0]}")
                    sheet_name = sheet_names[0]
                df = pd.read_excel(file_path, sheet_name=sheet_name, header=header_row)
            else:
                df = pd.read_excel(file_path, header=header_row)

            logger.info(f"读取到数据: {len(df)} 行, {len(df.columns)} 列")

            if df.empty:
                return {"success": False, "error": "Excel 文件为空"}

            # 清理列名
            df.columns = [str(c) for c in df.columns]
            table_name = self.excel_storage._sanitize_table_name(filename)
            results["table_name"] = table_name
            results["field_count"] = len(df.columns)
            logger.info(f"表名: {table_name}, 字段数: {len(df.columns)}")

            # 3. 初始化 RAG (如果需要)
            if not self.rag._initialized:
                self.rag._init_vector_store()

            # 4. 为每个字段生成描述并索引
            all_fields_data = {}
            for col in df.columns:
                # 采样示例值
                sample_values = df[col].dropna().head(sample_size).tolist()
                all_fields_data[col] = sample_values

            # 批量生成描述（避免过多 API 调用）
            indexed_count = 0
            for col in df.columns:
                try:
                    sample_values = all_fields_data[col]

                    # 生成描述
                    description = await self.generate_field_description(
                        table_name=table_name,
                        field_name=col,
                        sample_values=sample_values,
                        all_fields=all_fields_data
                    )

                    # 存入 RAG
                    self.rag.index_field(
                        table_name=table_name,
                        field_name=col,
                        field_description=description,
                        sample_values=[str(v) for v in sample_values[:5]]
                    )

                    indexed_count += 1
                    results["indexed_fields"].append({
                        "field": col,
                        "description": description
                    })

                    logger.info(f"字段已索引: {table_name}.{col}")

                except Exception as e:
                    error_msg = f"字段 {col} 索引失败: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            # 5. 存储到 MySQL
            logger.info(f"开始存储到MySQL: {filename}")
            store_result = await self.excel_storage.store_excel(
                file_path=file_path,
                filename=filename,
                sheet_name=sheet_name,
                header_row=header_row
            )

            if store_result.get("success"):
                results["mysql_table"] = store_result.get("table_name")
                results["row_count"] = store_result.get("row_count")
            else:
                results["mysql_warning"] = "MySQL 存储失败: " + str(store_result.get("error"))

            results["indexed_count"] = indexed_count
            logger.info(f"表 {table_name} RAG 索引构建完成，共 {indexed_count} 个字段")

            return results

        except Exception as e:
            logger.error(f"构建 RAG 索引失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def index_document_table(
        self,
        doc_id: str,
        filename: str,
        table_data: Dict[str, Any],
        source_doc_type: str
    ) -> Dict[str, Any]:
        """
        为非结构化文档中提取的表格建立 MySQL 存储和 RAG 索引

        Args:
            doc_id: 源文档 ID
            filename: 源文件名
            table_data: 表格数据，支持两种格式:
                1. docx/txt格式: {"rows": [["col1", "col2"], ["val1", "val2"]], ...}
                2. md格式: {"headers": [...], "rows": [...], ...}
            source_doc_type: 源文档类型 (docx/md/txt)

        Returns:
            索引构建结果
        """
        results = {
            "success": True,
            "table_name": "",
            "field_count": 0,
            "indexed_fields": [],
            "errors": []
        }

        try:
            # 兼容两种格式
            if "headers" in table_data:
                # md 格式：headers 和 rows 分开
                columns = table_data.get("headers", [])
                data_rows = table_data.get("rows", [])
            else:
                # docx/txt 格式：第一行作为表头
                rows = table_data.get("rows", [])
                if not rows or len(rows) < 2:
                    return {"success": False, "error": "表格数据不足"}
                columns = rows[0]
                data_rows = rows[1:]

            # 生成表名：源文件 + 表格索引
            base_name = self.excel_storage._sanitize_table_name(filename)
            table_name = f"{base_name}_table{table_data.get('table_index', 0)}"

            results["table_name"] = table_name
            results["field_count"] = len(columns)

            # 1. 初始化 RAG
            if not self.rag._initialized:
                self.rag._init_vector_store()

            # 2. 准备结构化数据
            structured_data = {
                "columns": columns,
                "rows": data_rows
            }

            # 3. 存储到 MySQL
            store_result = await self.excel_storage.store_structured_data(
                table_name=table_name,
                data=structured_data,
                source_doc_id=doc_id
            )

            if store_result.get("success"):
                results["mysql_table"] = store_result.get("table_name")
                results["row_count"] = store_result.get("row_count")
            else:
                results["mysql_warning"] = "MySQL 存储失败: " + str(store_result.get("error"))

            # 4. 为每个字段生成描述并索引
            all_fields_data = {}
            for i, col in enumerate(columns):
                col_values = [row[i] for row in data_rows if i < len(row)]
                all_fields_data[col] = col_values

            indexed_count = 0
            for col in columns:
                try:
                    col_values = all_fields_data.get(col, [])

                    # 生成描述
                    description = await self.generate_field_description(
                        table_name=table_name,
                        field_name=col,
                        sample_values=col_values[:10],
                        all_fields=all_fields_data
                    )

                    # 存入 RAG
                    self.rag.index_field(
                        table_name=table_name,
                        field_name=col,
                        field_description=description,
                        sample_values=[str(v) for v in col_values[:5]]
                    )

                    indexed_count += 1
                    results["indexed_fields"].append({
                        "field": col,
                        "description": description
                    })

                    logger.info(f"文档表格字段已索引: {table_name}.{col}")

                except Exception as e:
                    error_msg = f"字段 {col} 索引失败: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            results["indexed_count"] = indexed_count
            logger.info(f"文档表格 {table_name} RAG 索引构建完成，共 {indexed_count} 个字段")

            return results

        except Exception as e:
            logger.error(f"构建文档表格 RAG 索引失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def query_table_by_natural_language(
        self,
        user_query: str,
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        根据自然语言查询相关表字段

        Args:
            user_query: 用户查询
            top_k: 返回数量

        Returns:
            匹配的字段信息
        """
        try:
            # 1. RAG 检索
            rag_results = self.rag.retrieve(user_query, top_k=top_k)

            # 2. 解析检索结果
            matched_fields = []
            for result in rag_results:
                metadata = result.get("metadata", {})
                matched_fields.append({
                    "table_name": metadata.get("table_name", ""),
                    "field_name": metadata.get("field_name", ""),
                    "description": result.get("content", ""),
                    "score": result.get("score", 0),
                    "sample_values": []  # 可以后续补充
                })

            return {
                "success": True,
                "query": user_query,
                "matched_fields": matched_fields,
                "count": len(matched_fields)
            }

        except Exception as e:
            logger.error(f"查询失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_table_fields_with_description(
        self,
        table_name: str
    ) -> List[Dict[str, Any]]:
        """
        获取表的字段及其描述

        Args:
            table_name: 表名

        Returns:
            字段列表
        """
        try:
            # 从 RAG 检索该表的所有字段
            results = self.rag.retrieve_by_table(table_name, top_k=50)

            fields = []
            for result in results:
                metadata = result.get("metadata", {})
                fields.append({
                    "table_name": metadata.get("table_name", ""),
                    "field_name": metadata.get("field_name", ""),
                    "description": result.get("content", ""),
                    "score": result.get("score", 0)
                })

            return fields

        except Exception as e:
            logger.error(f"获取字段失败: {str(e)}")
            return []

    async def rebuild_all_table_indexes(self) -> Dict[str, Any]:
        """
        重建所有表的 RAG 索引

        从 MySQL 读取所有表结构，重新生成描述并索引
        """
        try:
            # 清空现有索引
            self.rag.clear()

            # 获取所有表
            tables = await self.excel_storage.list_tables()

            results = {
                "success": True,
                "tables_processed": 0,
                "total_fields": 0,
                "errors": []
            }

            for table_name in tables:
                try:
                    # 获取表结构
                    schema = await self.excel_storage.get_table_schema(table_name)

                    if not schema:
                        continue

                    # 初始化 RAG
                    if not self.rag._initialized:
                        self.rag._init_vector_store()

                    # 为每个字段生成描述并索引
                    for col_info in schema:
                        field_name = col_info.get("COLUMN_NAME", "")
                        if field_name in ["id", "created_at", "updated_at"]:
                            continue

                        # 采样数据
                        samples = await self.excel_storage.query_table(
                            table_name,
                            columns=[field_name],
                            limit=10
                        )
                        sample_values = [r.get(field_name) for r in samples if r.get(field_name)]

                        # 生成描述
                        description = await self.generate_field_description(
                            table_name=table_name,
                            field_name=field_name,
                            sample_values=sample_values
                        )

                        # 索引
                        self.rag.index_field(
                            table_name=table_name,
                            field_name=field_name,
                            field_description=description,
                            sample_values=[str(v) for v in sample_values[:5]]
                        )

                        results["total_fields"] += 1

                    results["tables_processed"] += 1
                    logger.info(f"表 {table_name} 索引重建完成")

                except Exception as e:
                    error_msg = f"表 {table_name} 索引失败: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            logger.info(f"全部 {results['tables_processed']} 个表索引重建完成")
            return results

        except Exception as e:
            logger.error(f"重建索引失败: {str(e)}")
            return {"success": False, "error": str(e)}


# ==================== 全局单例 ====================

table_rag_service = TableRAGService()
