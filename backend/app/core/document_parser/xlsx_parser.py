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

            # 检查 DataFrame 是否为空（但如果有列名，仍算有效）
            if df is None:
                return ParseResult(
                    success=False,
                    error=f"工作表 '{target_sheet}' 读取失败"
                )

            # 如果 DataFrame 为空但有列名（比如模板文件），仍算有效
            if df.empty and len(df.columns) == 0:
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

        # 常见的命名空间
        COMMON_NAMESPACES = [
            'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'http://schemas.openxmlformats.org/spreadsheetml/2005/main',
            'http://schemas.openxmlformats.org/spreadsheetml/2004/main',
            'http://schemas.openxmlformats.org/spreadsheetml/2003/main',
        ]

        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # 尝试多种可能的 workbook.xml 路径
                possible_paths = ['xl/workbook.xml', 'xl\\workbook.xml', 'workbook.xml']
                content = None
                for path in possible_paths:
                    if path in z.namelist():
                        content = z.read(path)
                        logger.info(f"找到 workbook.xml at: {path}")
                        break

                if content is None:
                    logger.warning(f"未找到 workbook.xml，文件列表: {z.namelist()[:10]}")
                    return []

                root = ET.fromstring(content)

                sheet_names = []

                # 方法1：尝试带命名空间的查找
                for ns in COMMON_NAMESPACES:
                    sheet_elements = root.findall(f'.//{{{ns}}}sheet')
                    if sheet_elements:
                        for sheet in sheet_elements:
                            name = sheet.get('name')
                            if name:
                                sheet_names.append(name)
                        if sheet_names:
                            logger.info(f"使用命名空间 {ns} 提取工作表: {sheet_names}")
                            return sheet_names

                # 方法2：不使用命名空间，直接查找所有 sheet 元素
                if not sheet_names:
                    for elem in root.iter():
                        if elem.tag.endswith('sheet') and elem.tag != 'sheets':
                            name = elem.get('name')
                            if name:
                                sheet_names.append(name)
                            for child in elem:
                                if child.tag.endswith('sheet') or child.tag == 'sheet':
                                    name = child.get('name')
                                    if name and name not in sheet_names:
                                        sheet_names.append(name)

                # 方法3：直接从 XML 文本中正则匹配 sheet name
                if not sheet_names:
                    import re
                    xml_str = content.decode('utf-8', errors='ignore')
                    matches = re.findall(r'<sheet\s+[^>]*name=["\']([^"\']+)["\']', xml_str, re.IGNORECASE)
                    if matches:
                        sheet_names = matches
                        logger.info(f"使用正则提取工作表: {sheet_names}")

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

        # 常见的命名空间
        COMMON_NAMESPACES = [
            'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
            'http://schemas.openxmlformats.org/spreadsheetml/2005/main',
            'http://schemas.openxmlformats.org/spreadsheetml/2004/main',
            'http://schemas.openxmlformats.org/spreadsheetml/2003/main',
        ]

        def find_elements_with_ns(root, tag_name):
            """灵活查找元素，支持任意命名空间"""
            results = []
            # 方法1：用固定命名空间
            for ns in COMMON_NAMESPACES:
                try:
                    elems = root.findall(f'.//{{{ns}}}{tag_name}')
                    if elems:
                        results.extend(elems)
                except:
                    pass
            # 方法2：不带命名空间查找
            if not results:
                for elem in root.iter():
                    if elem.tag.endswith('}' + tag_name):
                        results.append(elem)
            return results

        with zipfile.ZipFile(file_path, 'r') as z:
            # 获取工作表名称
            sheet_names = self._extract_sheet_names_from_xml(file_path)
            if not sheet_names:
                raise ValueError("无法从 Excel 文件中找到工作表")

            # 确定要读取的工作表
            target_sheet = sheet_name if sheet_name and sheet_name in sheet_names else sheet_names[0]
            sheet_index = sheet_names.index(target_sheet) + 1  # sheet1.xml, sheet2.xml, ...

            # 读取 shared strings - 尝试多种路径
            shared_strings = []
            ss_paths = ['xl/sharedStrings.xml', 'xl\\sharedStrings.xml', 'sharedStrings.xml']
            for ss_path in ss_paths:
                if ss_path in z.namelist():
                    try:
                        ss_content = z.read(ss_path)
                        ss_root = ET.fromstring(ss_content)
                        for si in find_elements_with_ns(ss_root, 'si'):
                            t_elements = [c for c in si if c.tag.endswith('}t') or c.tag == 't']
                            if t_elements:
                                shared_strings.append(t_elements[0].text or '')
                            else:
                                shared_strings.append('')
                        break
                    except Exception as e:
                        logger.warning(f"读取 sharedStrings 失败: {e}")

            # 读取工作表 - 尝试多种可能的路径
            sheet_content = None
            sheet_paths = [
                f'xl/worksheets/sheet{sheet_index}.xml',
                f'xl\\worksheets\\sheet{sheet_index}.xml',
                f'worksheets/sheet{sheet_index}.xml',
            ]
            for sp in sheet_paths:
                if sp in z.namelist():
                    sheet_content = z.read(sp)
                    break

            if sheet_content is None:
                raise ValueError(f"工作表文件 sheet{sheet_index}.xml 不存在")

            root = ET.fromstring(sheet_content)

            # 收集所有行数据
            all_rows = []
            headers = {}

            for row in find_elements_with_ns(root, 'row'):
                row_idx = int(row.get('r', 0))
                row_cells = {}
                for cell in find_elements_with_ns(row, 'c'):
                    cell_ref = cell.get('r', '')
                    col_letters = ''.join(filter(str.isalpha, cell_ref))
                    cell_type = cell.get('t', 'n')
                    v_elements = find_elements_with_ns(cell, 'v')
                    v = v_elements[0] if v_elements else None

                    if v is not None and v.text:
                        if cell_type == 's':
                            try:
                                row_cells[col_letters] = shared_strings[int(v.text)]
                            except (ValueError, IndexError):
                                row_cells[col_letters] = v.text
                        elif cell_type == 'b':
                            row_cells[col_letters] = v.text == '1'
                        else:
                            row_cells[col_letters] = v.text
                    else:
                        row_cells[col_letters] = None

                if row_idx == header_row + 1:
                    headers = {**row_cells}
                elif row_idx > header_row + 1:
                    all_rows.append(row_cells)

            # 构建 DataFrame
            if headers:
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
