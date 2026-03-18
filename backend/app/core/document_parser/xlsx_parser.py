"""
Excel 文件解析器 - 解析 .xlsx 和 .xls 文件
"""
from typing import Any, Dict, List, Optional
from pathlib import Path
import pandas as pd
import logging

from .base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class XlsxParser(BaseParser):
    """Excel 文件解析器"""

    def __init__(self):
        super().__init__()
        self.supported_extensions = ['.xlsx', '.xls']
        self.parser_name = "excel_parser"

    def parse(
        self,
        file_path: str,
        sheet_name: Optional[str | int] = 0,
        header_row: int = 0,
        **kwargs
    ) -> ParseResult:
        """
        解析 Excel 文件

        Args:
            file_path: 文件路径
            sheet_name: 工作表名称或索引，默认为第一个工作表
            header_row: 表头所在的行索引，默认为 0
            **kwargs: 其他参数传递给 pandas.read_excel

        Returns:
            ParseResult: 解析结果
        """
        path = Path(file_path)

        # 检查文件是否存在
        if not path.exists():
            return ParseResult(
                success=False,
                error=f"File not found: {file_path}"
            )

        # 检查文件扩展名
        if path.suffix.lower() not in self.supported_extensions:
            return ParseResult(
                success=False,
                error=f"Unsupported file type: {path.suffix}"
            )

        # 检查文件大小
        file_size = path.stat().st_size
        if file_size == 0:
            return ParseResult(
                success=False,
                error=f"File is empty: {file_path}"
            )

        try:
            # 尝试读取 Excel 文件，检查是否有工作表
            xls_file = pd.ExcelFile(file_path)
            sheet_names = xls_file.sheet_names

            if not sheet_names:
                return ParseResult(
                    success=False,
                    error=f"Excel 文件没有找到任何工作表: {file_path}"
                )

            # 验证请求的工作表索引/名称
            target_sheet = None
            if sheet_name is not None:
                if isinstance(sheet_name, int) and sheet_name < len(sheet_names):
                    target_sheet = sheet_names[sheet_name]
                elif isinstance(sheet_name, str) and sheet_name in sheet_names:
                    target_sheet = sheet_name
                else:
                    # 如果指定的 sheet_name 无效，使用第一个工作表
                    target_sheet = sheet_names[0]
            else:
                # 默认使用第一个工作表
                target_sheet = sheet_names[0]

            # 读取 Excel 文件
            df = pd.read_excel(
                file_path,
                sheet_name=target_sheet,
                header=header_row,
                **kwargs
            )

            # 检查 DataFrame 是否为空
            if df.empty:
                return ParseResult(
                    success=False,
                    error=f"工作表 '{target_sheet}' 为空，请检查 Excel 文件内容"
                )

            # 转换为可序列化的数据
            data = self._df_to_dict(df)

            # 构建元数据
            metadata = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "sheet_count": len(sheet_names),
                "sheet_names": sheet_names,
                "current_sheet": target_sheet,
                "row_count": len(df),
                "column_count": len(df.columns) if not df.empty else 0,
                "columns": df.columns.tolist() if not df.empty else [],
                "file_size": file_size
            }

            return ParseResult(
                success=True,
                data=data,
                metadata=metadata
            )

        except IndexError as e:
            logger.error(f"工作表索引错误: {str(e)}")
            # 工作表索引超出范围时，尝试使用第一个工作表
            try:
                xls_file = pd.ExcelFile(file_path)
                sheet_names = xls_file.sheet_names
                if sheet_names:
                    df = pd.read_excel(
                        file_path,
                        sheet_name=sheet_names[0],
                        header=header_row,
                        **kwargs
                    )

                    data = self._df_to_dict(df)
                    metadata = {
                        "filename": path.name,
                        "extension": path.suffix.lower(),
                        "sheet_count": len(sheet_names),
                        "sheet_names": sheet_names,
                        "current_sheet": sheet_names[0],
                        "row_count": len(df),
                        "column_count": len(df.columns) if not df.empty else 0,
                        "columns": df.columns.tolist() if not df.empty else [],
                        "file_size": path.stat().st_size
                    }

                    return ParseResult(
                        success=True,
                        data=data,
                        metadata=metadata
                    )
                else:
                    return ParseResult(
                        success=False,
                        error=f"Excel 文件没有有效的工作表"
                    )
            except Exception as e2:
                logger.error(f"重试解析失败: {str(e2)}")
                return ParseResult(
                    success=False,
                    error=f"无法解析 Excel 文件: {str(e)}"
                )

        except Exception as e:
            logger.error(f"解析 Excel 文件时出错: {str(e)}")
            return ParseResult(
                success=False,
                error=f"Failed to parse Excel file: {str(e)}"
            )

    def parse_all_sheets(self, file_path: str, **kwargs) -> ParseResult:
        """
        解析 Excel 文件的所有工作表

        Args:
            file_path: 文件路径
            **kwargs: 其他参数传递给 pandas.read_excel

        Returns:
            ParseResult: 解析结果
        """
        path = Path(file_path)

        # 检查文件是否存在
        if not path.exists():
            return ParseResult(
                success=False,
                error=f"File not found: {file_path}"
            )

        if path.suffix.lower() not in self.supported_extensions:
            return ParseResult(
                success=False,
                error=f"Unsupported file type: {path.suffix}"
            )

        # 检查文件大小
        file_size = path.stat().st_size
        if file_size == 0:
            return ParseResult(
                success=False,
                error=f"File is empty: {file_path}"
            )

        try:
            # 读取所有工作表
            all_data = pd.read_excel(file_path, sheet_name=None, **kwargs)

            # 检查是否成功读取到数据
            if not all_data or len(all_data) == 0:
                return ParseResult(
                    success=False,
                    error=f"无法读取 Excel 文件或文件为空: {file_path}"
                )

            # 转换为可序列化的数据
            sheets_data = {}
            for sheet_name, df in all_data.items():
                sheets_data[sheet_name] = self._df_to_dict(df)

            # 获取所有工作表名称
            all_sheets = list(all_data.keys())

            # 构建元数据
            total_rows = sum(len(df) for df in all_data.values())
            metadata = {
                "filename": path.name,
                "extension": path.suffix.lower(),
                "sheet_count": len(all_sheets),
                "sheet_names": all_sheets,
                "total_rows": total_rows,
                "file_size": file_size
            }

            return ParseResult(
                success=True,
                data={"sheets": sheets_data},
                metadata=metadata
            )

        except Exception as e:
            logger.error(f"Failed to parse Excel file: {str(e)}")
            return ParseResult(
                success=False,
                error=f"Failed to parse Excel file: {str(e)}"
            )

    def _get_sheet_names(self, file_path: str) -> List[str]:
        """获取 Excel 文件中的所有工作表名称"""
        try:
            xls = pd.ExcelFile(file_path)
            sheet_names = xls.sheet_names
            if not sheet_names:
                return []
            return sheet_names
        except Exception as e:
            logger.error(f"获取工作表名称失败: {str(e)}")
            return []

    def _df_to_dict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        将 DataFrame 转换为字典，处理 NaN 值

        Args:
            df: pandas DataFrame

        Returns:
            Dict[str, Any]: 转换后的字典
        """
        # 将 NaN 替换为 None
        df = df.replace({pd.NA: None, float('nan'): None})

        # 转换为字典列表（每一行一个字典）
        rows = df.to_dict(orient='records')

        return {
            "columns": df.columns.tolist(),
            "rows": rows,
            "row_count": len(rows),
            "column_count": len(df.columns) if not df.empty else 0
        }
