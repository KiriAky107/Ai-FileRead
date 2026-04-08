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

            # 如果 pandas 返回空列表，尝试从 XML 提取
            if not sheet_names:
                sheet_names = self._extract_sheet_names_from_xml(file_path)
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
            df = None
            try:
                df = pd.read_excel(
                    file_path,
                    sheet_name=target_sheet,
                    header=header_row,
                    **kwargs
                )
            except Exception as e:
                logger.warning(f"pandas 读取 Excel 失败，尝试 XML 方式: {e}")
                # pandas 读取失败，尝试 XML 方式
                df = self._read_excel_sheet_xml(file_path, sheet_name=target_sheet, header_row=header_row)

            # 检查 DataFrame 是否为空
            if df is None or df.empty:
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
            all_data = None
            try:
                all_data = pd.read_excel(file_path, sheet_name=None, **kwargs)
            except Exception as e:
                logger.warning(f"pandas 读取所有工作表失败: {e}")

            # 如果 pandas 失败，尝试 XML 方式
            if all_data is None or len(all_data) == 0:
                sheet_names = self._extract_sheet_names_from_xml(file_path)
                if not sheet_names:
                    return ParseResult(
                        success=False,
                        error=f"无法读取 Excel 文件或文件为空: {file_path}"
                    )
                # 使用 XML 方式读取每个工作表
                all_data = {}
                for sheet_name in sheet_names:
                    df = self._read_excel_sheet_xml(file_path, sheet_name=sheet_name, header_row=0)
                    if df is not None and not df.empty:
                        all_data[sheet_name] = df

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
            if sheet_names:
                return sheet_names
            # pandas 返回空列表，尝试从 XML 提取
            return self._extract_sheet_names_from_xml(file_path)
        except Exception as e:
            logger.error(f"获取工作表名称失败: {str(e)}")
            # 尝试从 XML 提取
            return self._extract_sheet_names_from_xml(file_path)

    def _extract_sheet_names_from_xml(self, file_path: str) -> List[str]:
        """
        从 Excel 文件的 XML 中提取工作表名称

        某些 Excel 文件由于包含非标准元素（如 mc:AlternateContent），
        pandas/openpyxl 无法正确解析工作表列表，此时需要直接从 XML 中提取。

        Args:
            file_path: Excel 文件路径

        Returns:
            工作表名称列表
        """
        import zipfile
        from xml.etree import ElementTree as ET

        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                if 'xl/workbook.xml' not in z.namelist():
                    return []
                content = z.read('xl/workbook.xml')
                root = ET.fromstring(content)

                # 命名空间
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

                sheet_names = []
                for sheet in root.findall('.//main:sheet', ns):
                    name = sheet.get('name')
                    if name:
                        sheet_names.append(name)

                logger.info(f"从 XML 提取工作表: {sheet_names}")
                return sheet_names
        except Exception as e:
            logger.error(f"从 XML 提取工作表名称失败: {e}")
            return []

    def _read_excel_sheet_xml(self, file_path: str, sheet_name: str = None, header_row: int = 0) -> pd.DataFrame:
        """
        从 XML 直接读取 Excel 工作表数据

        当 pandas 无法正确解析时使用此方法。

        Args:
            file_path: Excel 文件路径
            sheet_name: 工作表名称（如果为 None，读取第一个工作表）
            header_row: 表头行号（0-indexed）

        Returns:
            DataFrame
        """
        import zipfile
        from xml.etree import ElementTree as ET

        with zipfile.ZipFile(file_path, 'r') as z:
            # 获取工作表名称
            sheet_names = self._extract_sheet_names_from_xml(file_path)
            if not sheet_names:
                raise ValueError("无法从 Excel 文件中找到工作表")

            # 确定要读取的工作表
            target_sheet = sheet_name if sheet_name and sheet_name in sheet_names else sheet_names[0]
            sheet_index = sheet_names.index(target_sheet) + 1  # sheet1.xml, sheet2.xml, ...

            # 读取 shared strings
            shared_strings = []
            if 'xl/sharedStrings.xml' in z.namelist():
                ss_content = z.read('xl/sharedStrings.xml')
                ss_root = ET.fromstring(ss_content)
                ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                for si in ss_root.findall('.//main:si', ns):
                    t = si.find('.//main:t', ns)
                    if t is not None:
                        shared_strings.append(t.text or '')
                    else:
                        shared_strings.append('')

            # 读取工作表
            sheet_file = f'xl/worksheets/sheet{sheet_index}.xml'
            if sheet_file not in z.namelist():
                raise ValueError(f"工作表文件 {sheet_file} 不存在")

            sheet_content = z.read(sheet_file)
            root = ET.fromstring(sheet_content)
            ns = {'main': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

            # 收集所有行数据
            all_rows = []
            headers = {}

            for row in root.findall('.//main:row', ns):
                row_idx = int(row.get('r', 0))
                row_cells = {}
                for cell in row.findall('main:c', ns):
                    cell_ref = cell.get('r', '')
                    col_letters = ''.join(filter(str.isalpha, cell_ref))
                    cell_type = cell.get('t', 'n')
                    v = cell.find('main:v', ns)

                    if v is not None and v.text:
                        if cell_type == 's':
                            # shared string
                            try:
                                row_cells[col_letters] = shared_strings[int(v.text)]
                            except (ValueError, IndexError):
                                row_cells[col_letters] = v.text
                        elif cell_type == 'b':
                            # boolean
                            row_cells[col_letters] = v.text == '1'
                        else:
                            row_cells[col_letters] = v.text
                    else:
                        row_cells[col_letters] = None

                # 处理表头行
                if row_idx == header_row + 1:
                    headers = {**row_cells}
                elif row_idx > header_row + 1:
                    all_rows.append(row_cells)

            # 构建 DataFrame
            if headers:
                # 按原始列顺序排列
                col_order = list(headers.keys())
                df = pd.DataFrame(all_rows)
                if not df.empty:
                    df = df[col_order]
                df.columns = [headers.get(col, col) for col in df.columns]
            else:
                df = pd.DataFrame(all_rows)

            return df

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
