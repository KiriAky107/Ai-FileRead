"""
表格模板填写服务

从非结构化文档中检索信息并填写到表格模板
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.database import mongodb
from app.services.llm_service import llm_service
from app.core.document_parser import ParserFactory
from app.services.markdown_ai_service import markdown_ai_service

logger = logging.getLogger(__name__)


@dataclass
class TemplateField:
    """模板字段"""
    cell: str  # 单元格位置，如 "A1"
    name: str  # 字段名称
    field_type: str = "text"  # 字段类型: text/number/date
    required: bool = True
    hint: str = ""  # 字段提示词


@dataclass
class SourceDocument:
    """源文档"""
    doc_id: str
    filename: str
    doc_type: str
    content: str = ""
    structured_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FillResult:
    """填写结果"""
    field: str
    values: List[Any] = None  # 支持多个值
    value: Any = ""  # 保留兼容
    source: str = ""  # 来源文档
    confidence: float = 1.0  # 置信度

    def __post_init__(self):
        if self.values is None:
            self.values = []


class TemplateFillService:
    """表格填写服务"""

    def __init__(self):
        self.llm = llm_service

    async def fill_template(
        self,
        template_fields: List[TemplateField],
        source_doc_ids: Optional[List[str]] = None,
        source_file_paths: Optional[List[str]] = None,
        user_hint: Optional[str] = None,
        template_id: Optional[str] = None,
        template_file_type: Optional[str] = "xlsx"
    ) -> Dict[str, Any]:
        """
        填写表格模板

        Args:
            template_fields: 模板字段列表
            source_doc_ids: 源文档 MongoDB ID 列表
            source_file_paths: 源文档文件路径列表
            user_hint: 用户提示（如"请从合同文档中提取"）
            template_id: 模板文件路径（用于重新生成表头）
            template_file_type: 模板文件类型

        Returns:
            填写结果
        """
        filled_data = {}
        fill_details = []

        logger.info(f"开始填表: {len(template_fields)} 个字段, {len(source_doc_ids or [])} 个源文档")
        logger.info(f"source_doc_ids: {source_doc_ids}")
        logger.info(f"source_file_paths: {source_file_paths}")

        # 1. 加载源文档内容
        source_docs = await self._load_source_documents(source_doc_ids, source_file_paths)

        logger.info(f"加载了 {len(source_docs)} 个源文档")

        # 打印每个加载的文档的详细信息
        for i, doc in enumerate(source_docs):
            logger.info(f"  文档[{i}]: id={doc.doc_id}, filename={doc.filename}, doc_type={doc.doc_type}")
            logger.info(f"    content长度: {len(doc.content)}, structured_data keys: {list(doc.structured_data.keys()) if doc.structured_data else 'None'}")

        if not source_docs:
            logger.warning("没有找到源文档，填表结果将全部为空")

        # 3. 检查是否需要使用源文档重新生成表头
        # 条件：源文档已加载 AND 现有字段看起来是自动生成的（如"字段1"、"字段2"）
        needs_regenerate_headers = (
            len(source_docs) > 0 and
            len(template_fields) > 0 and
            all(self._is_auto_generated_field(f.name) for f in template_fields)
        )

        if needs_regenerate_headers:
            logger.info(f"检测到自动生成表头，尝试使用源文档重新生成... (当前字段: {[f.name for f in template_fields]})")

            # 将 SourceDocument 转换为 source_contents 格式
            source_contents = []
            for doc in source_docs:
                structured = doc.structured_data if doc.structured_data else {}

                # 获取标题
                titles = structured.get("titles", [])
                if not titles:
                    titles = []

                # 获取表格
                tables = structured.get("tables", [])
                tables_count = len(tables) if tables else 0

                # 生成表格摘要
                tables_summary = ""
                if tables:
                    tables_summary = "\n【文档中的表格】:\n"
                    for idx, table in enumerate(tables[:5]):
                        if isinstance(table, dict):
                            headers = table.get("headers", [])
                            rows = table.get("rows", [])
                            if headers:
                                tables_summary += f"表格{idx+1}表头: {', '.join(str(h) for h in headers)}\n"
                            if rows:
                                tables_summary += f"表格{idx+1}前3行: "
                                for row_idx, row in enumerate(rows[:3]):
                                    if isinstance(row, list):
                                        tables_summary += " | ".join(str(c) for c in row) + "; "
                                    elif isinstance(row, dict):
                                        tables_summary += " | ".join(str(row.get(h, "")) for h in headers if headers) + "; "
                                tables_summary += "\n"

                source_contents.append({
                    "filename": doc.filename,
                    "doc_type": doc.doc_type,
                    "content": doc.content[:5000] if doc.content else "",
                    "titles": titles[:10] if titles else [],
                    "tables_count": tables_count,
                    "tables_summary": tables_summary
                })

            # 使用源文档内容重新生成表头
            if template_id and template_file_type:
                logger.info(f"使用源文档重新生成表头: template_id={template_id}, template_file_type={template_file_type}")
                new_fields = await self.get_template_fields_from_file(
                    template_id,
                    template_file_type,
                    source_contents=source_contents
                )
                if new_fields and len(new_fields) > 0:
                    logger.info(f"成功重新生成表头: {[f.name for f in new_fields]}")
                    template_fields = new_fields
                else:
                    logger.warning("重新生成表头返回空结果，使用原始字段")
            else:
                logger.warning("无法重新生成表头：缺少 template_id 或 template_file_type")
        else:
            if source_docs and template_fields:
                logger.info(f"表头看起来正常（非自动生成），无需重新生成: {[f.name for f in template_fields[:5]]}")

        # 2. 对每个字段进行提取
        for idx, field in enumerate(template_fields):
            try:
                logger.info(f"提取字段 [{idx+1}/{len(template_fields)}]: {field.name}")
                # 从源文档中提取字段值
                result = await self._extract_field_value(
                    field=field,
                    source_docs=source_docs,
                    user_hint=user_hint
                )

                # 存储结果 - 使用 values 数组
                filled_data[field.name] = result.values if result.values else [""]
                fill_details.append({
                    "field": field.name,
                    "cell": field.cell,
                    "values": result.values,
                    "value": result.value,
                    "source": result.source,
                    "confidence": result.confidence
                })

                logger.info(f"字段 {field.name} 填写完成: {len(result.values)} 个值")

            except Exception as e:
                logger.error(f"填写字段 {field.name} 失败: {str(e)}", exc_info=True)
                filled_data[field.name] = [f"[提取失败: {str(e)}]"]
                fill_details.append({
                    "field": field.name,
                    "cell": field.cell,
                    "values": [f"[提取失败]"],
                    "value": f"[提取失败]",
                    "source": "error",
                    "confidence": 0.0
                })

        # 计算最大行数
        max_rows = max(len(v) for v in filled_data.values()) if filled_data else 1
        logger.info(f"填表完成: {len(filled_data)} 个字段, 最大行数: {max_rows}")

        return {
            "success": True,
            "filled_data": filled_data,
            "fill_details": fill_details,
            "source_doc_count": len(source_docs),
            "max_rows": max_rows
        }

    async def _load_source_documents(
        self,
        source_doc_ids: Optional[List[str]] = None,
        source_file_paths: Optional[List[str]] = None
    ) -> List[SourceDocument]:
        """
        加载源文档内容

        Args:
            source_doc_ids: MongoDB 文档 ID 列表
            source_file_paths: 源文档文件路径列表

        Returns:
            源文档列表
        """
        source_docs = []

        # 1. 从 MongoDB 加载文档
        if source_doc_ids:
            for doc_id in source_doc_ids:
                try:
                    doc = await mongodb.get_document(doc_id)
                    if doc:
                        sd = doc.get("structured_data", {})
                        sd_keys = list(sd.keys()) if sd else []
                        logger.info(f"从MongoDB加载文档: {doc_id}, doc_type={doc.get('doc_type')}, structured_data keys={sd_keys}")

                        # 如果 structured_data 为空，但有 file_path，尝试重新解析文件
                        doc_content = doc.get("content", "")
                        if not sd or (not sd.get("tables") and not sd.get("headers") and not sd.get("rows")):
                            file_path = doc.get("metadata", {}).get("file_path")
                            if file_path:
                                logger.info(f"  structured_data 为空，尝试重新解析文件: {file_path}")
                                try:
                                    parser = ParserFactory.get_parser(file_path)
                                    result = parser.parse(file_path)
                                    if result.success and result.data:
                                        if result.data.get("structured_data"):
                                            sd = result.data.get("structured_data")
                                            logger.info(f"  重新解析成功，structured_data keys: {list(sd.keys())}")
                                        elif result.data.get("tables"):
                                            sd = {"tables": result.data.get("tables", [])}
                                            logger.info(f"  使用 data.tables，tables数量: {len(sd.get('tables', []))}")
                                        elif result.data.get("rows"):
                                            sd = result.data
                                            logger.info(f"  使用 data.rows 格式")
                                        if result.data.get("content"):
                                            doc_content = result.data.get("content", "")
                                    else:
                                        logger.warning(f"  重新解析失败: {result.error if result else 'unknown'}")
                                except Exception as parse_err:
                                    logger.error(f"  重新解析文件异常: {str(parse_err)}")

                        if sd.get("tables"):
                            logger.info(f"  tables数量: {len(sd.get('tables', []))}")
                            if sd["tables"]:
                                first_table = sd["tables"][0]
                                logger.info(f"  第一表格: headers={first_table.get('headers', [])[:3]}..., rows数量={len(first_table.get('rows', []))}")

                        source_docs.append(SourceDocument(
                            doc_id=doc_id,
                            filename=doc.get("metadata", {}).get("original_filename", "unknown"),
                            doc_type=doc.get("doc_type", "unknown"),
                            content=doc_content,
                            structured_data=sd
                        ))
                except Exception as e:
                    logger.error(f"从MongoDB加载文档失败 {doc_id}: {str(e)}")

        # 2. 从文件路径加载文档
        if source_file_paths:
            for file_path in source_file_paths:
                try:
                    parser = ParserFactory.get_parser(file_path)
                    result = parser.parse(file_path)
                    if result.success:
                        # result.data 的结构取决于解析器类型:
                        # - Excel 单 sheet: {columns: [...], rows: [...], row_count, column_count}
                        # - Excel 多 sheet: {sheets: {sheet_name: {columns, rows, ...}}}
                        # - Markdown: {content: "...", tables: [...], structured_data: {tables: [...]}}
                        # - Word/TXT: {content: "...", structured_data: {...}}
                        doc_data = result.data if result.data else {}
                        doc_content = doc_data.get("content", "") if isinstance(doc_data, dict) else ""

                        # 检查并提取 structured_data
                        doc_structured = {}
                        if isinstance(doc_data, dict):
                            logger.info(f"文档 {file_path} doc_data keys: {list(doc_data.keys())}")

                            # Excel 多 sheet
                            if "sheets" in doc_data:
                                doc_structured = doc_data
                                logger.info(f"  -> 使用 Excel 多 sheet 格式")
                            # Excel 单 sheet 或有 rows 的格式
                            elif "rows" in doc_data:
                                doc_structured = doc_data
                                logger.info(f"  -> 使用 rows 格式，列数: {len(doc_data.get('columns', []))}")
                            # Markdown 格式：tables 可能直接在 doc_data.tables 或在 structured_data.tables 中
                            elif "tables" in doc_data and doc_data["tables"]:
                                # Markdown: tables 直接在 doc_data 中
                                tables = doc_data["tables"]
                                first_table = tables[0]
                                doc_structured = {
                                    "headers": first_table.get("headers", []),
                                    "rows": first_table.get("rows", [])
                                }
                                logger.info(f"  -> 使用 doc_data.tables 格式，表头: {doc_structured.get('headers', [])[:5]}")
                            elif "structured_data" in doc_data and isinstance(doc_data["structured_data"], dict):
                                # Markdown: tables 在 structured_data 中
                                tables = doc_data["structured_data"].get("tables", [])
                                if tables:
                                    first_table = tables[0]
                                    doc_structured = {
                                        "headers": first_table.get("headers", []),
                                        "rows": first_table.get("rows", [])
                                    }
                                    logger.info(f"  -> 使用 structured_data.tables 格式，表头: {doc_structured.get('headers', [])[:5]}")
                                else:
                                    logger.warning(f"  -> structured_data.tables 为空")
                            else:
                                logger.warning(f"  -> 未识别的文档格式，无 structured_data")

                        source_docs.append(SourceDocument(
                            doc_id=file_path,
                            filename=result.metadata.get("filename", file_path.split("/")[-1]),
                            doc_type=result.metadata.get("extension", "unknown").replace(".", ""),
                            content=doc_content,
                            structured_data=doc_structured
                        ))
                        logger.info(f"从文件加载文档: {file_path}, content长度: {len(doc_content)}, structured数据: {bool(doc_structured)}")
                except Exception as e:
                    logger.error(f"从文件加载文档失败 {file_path}: {str(e)}")

        return source_docs

    async def _extract_field_value(
        self,
        field: TemplateField,
        source_docs: List[SourceDocument],
        user_hint: Optional[str] = None
    ) -> FillResult:
        """
        使用 LLM 从源文档中提取字段值

        Args:
            field: 字段定义
            source_docs: 源文档列表
            user_hint: 用户提示

        Returns:
            提取结果
        """
        if not source_docs:
            return FillResult(
                field=field.name,
                value="",
                source="无源文档",
                confidence=0.0
            )

        # 优先尝试直接从结构化数据中提取列值（适用于 Excel 等有 rows 的数据）
        direct_values = self._extract_values_from_structured_data(source_docs, field.name)
        if direct_values:
            logger.info(f"✅ 字段 {field.name} 直接从结构化数据提取到 {len(direct_values)} 个值")
            return FillResult(
                field=field.name,
                values=direct_values,
                value=direct_values[0] if direct_values else "",
                source="结构化数据直接提取",
                confidence=1.0
            )

        # 无法直接从结构化数据提取，尝试 AI 分析非结构化文档
        ai_structured = await self._analyze_unstructured_docs_for_fields(source_docs, field, user_hint)
        if ai_structured:
            logger.info(f"✅ 字段 {field.name} 通过 AI 分析结构化提取到数据")
            return ai_structured

        # 无法从结构化数据提取，使用 LLM
        logger.info(f"字段 {field.name} 无法直接从结构化数据提取，使用 LLM...")

        # 构建上下文文本 - 传入字段名，只提取该列数据
        context_text = self._build_context_text(source_docs, field_name=field.name, max_length=200000)

        # 构建提示词
        hint_text = field.hint if field.hint else f"请提取{field.name}的信息"
        if user_hint:
            hint_text = f"{user_hint}。{hint_text}"

        prompt = f"""你是一个专业的数据提取专家。请从以下文档内容中提取与"{field.name}"相关的所有信息。

提示词: {hint_text}

文档内容：
{context_text}

请分析文档结构（可能包含表格、标题段落等），找出所有与"{field.name}"相关的数据。
如果找到表格数据，返回多行值；如果是非表格段落，提取关键信息。

请严格按照以下 JSON 格式输出：
{{
    "values": ["第1行的值", "第2行的值", ...],
    "source": "数据来源描述",
    "confidence": 0.0到1.0之间的置信度
}}
"""

        # 调用 LLM
        messages = [
            {"role": "system", "content": "你是一个专业的数据提取助手。请严格按JSON格式输出。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )

            content = self.llm.extract_message_content(response)

            # 解析 JSON 响应
            import json
            import re

            extracted_values = []
            extracted_value = ""
            extracted_source = "LLM生成"
            confidence = 0.5

            logger.info(f"原始 LLM 返回: {content[:500]}")

            # ========== 步骤1: 彻底清理 markdown 和各种格式问题 ==========
            # 移除 ```json 和 ``` 标记
            cleaned = content.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            logger.info(f"清理后: {cleaned[:500]}")

            # ========== 步骤2: 定位 JSON 开始位置 ==========
            json_start = -1
            # 找到第一个 { 或 [
            for i, c in enumerate(cleaned):
                if c == '{' or c == '[':
                    json_start = i
                    break

            if json_start == -1:
                logger.warning(f"无法找到 JSON 开始位置")
                extracted_values = self._extract_values_from_text(cleaned, field.name)
            else:
                json_text = cleaned[json_start:]
                logger.info(f"JSON 开始位置: {json_start}, 内容: {json_text[:200]}")

                # ========== 步骤3: 尝试解析 JSON ==========
                # 3a. 尝试直接解析整个字符串
                try:
                    result = json.loads(json_text)
                    extracted_values = self._extract_values_from_json(result)
                    if extracted_values:
                        logger.info(f"✅ 直接解析成功，得到 {len(extracted_values)} 个值")
                    else:
                        logger.warning(f"直接解析成功但未提取到值")
                except json.JSONDecodeError as e:
                    logger.warning(f"直接解析失败: {e}, 尝试修复...")

                    # 3b. 尝试修复常见的 JSON 问题
                    # 尝试1: 找到配对的闭合括号
                    fixed_json = self._fix_json(json_text)
                    if fixed_json:
                        try:
                            result = json.loads(fixed_json)
                            extracted_values = self._extract_values_from_json(result)
                            if extracted_values:
                                logger.info(f"✅ 修复后解析成功，得到 {len(extracted_values)} 个值")
                        except json.JSONDecodeError as e2:
                            logger.warning(f"修复后仍然失败: {e2}")

                    # 3c. 如果以上都失败，使用正则直接从文本提取 values 数组
                    if not extracted_values:
                        extracted_values = self._extract_values_by_regex(cleaned)
                        if extracted_values:
                            logger.info(f"✅ 正则提取成功，得到 {len(extracted_values)} 个值")
                        else:
                            # 最后的备选：使用旧的文本提取
                            extracted_values = self._extract_values_from_text(cleaned, field.name)

            # 如果仍然没有提取到值
            if not extracted_values:
                extracted_values = [""]
                logger.warning(f"❌ 字段 {field.name} 没有提取到值")

            logger.info(f"✅✅ 字段 {field.name} 最终返回: {len(extracted_values)} 个值, 示例: {extracted_values[:3]}")

            return FillResult(
                field=field.name,
                values=extracted_values,
                value=extracted_values[0] if extracted_values else "",
                source=extracted_source,
                confidence=confidence
            )

        except Exception as e:
            logger.error(f"LLM 提取失败: {str(e)}")
            return FillResult(
                field=field.name,
                values=[""],
                value="",
                source=f"提取失败: {str(e)}",
                confidence=0.0
            )

    def _build_context_text(self, source_docs: List[SourceDocument], field_name: str = None, max_length: int = 8000) -> str:
        """
        构建上下文文本

        Args:
            source_docs: 源文档列表
            field_name: 需要提取的字段名（可选，用于只提取特定列）
            max_length: 最大字符数

        Returns:
            上下文文本
        """
        contexts = []
        total_length = 0

        for doc in source_docs:
            # 优先使用结构化数据（表格），其次使用文本内容
            doc_content = ""
            row_count = 0

            if doc.structured_data and doc.structured_data.get("sheets"):
                # parse_all_sheets 格式: {sheets: {sheet_name: {columns, rows}}}
                sheets = doc.structured_data.get("sheets", {})
                for sheet_name, sheet_data in sheets.items():
                    if isinstance(sheet_data, dict):
                        columns = sheet_data.get("columns", [])
                        rows = sheet_data.get("rows", [])
                        if rows and columns:
                            doc_content += f"\n【文档: {doc.filename} - {sheet_name}，共 {len(rows)} 行】\n"
                            # 如果指定了字段名，只提取该列数据
                            if field_name:
                                # 查找匹配的列（模糊匹配）
                                target_col = None
                                for col in columns:
                                    if field_name.lower() in str(col).lower() or str(col).lower() in field_name.lower():
                                        target_col = col
                                        break
                                if target_col:
                                    doc_content += f"列名: {target_col}\n"
                                    for row_idx, row in enumerate(rows):
                                        if isinstance(row, dict):
                                            val = row.get(target_col, "")
                                        elif isinstance(row, list) and target_col in columns:
                                            val = row[columns.index(target_col)]
                                        else:
                                            val = ""
                                        doc_content += f"行{row_idx+1}: {val}\n"
                                        row_count += 1
                                else:
                                    # 列名不匹配，输出所有列（但只输出关键列）
                                    doc_content += " | ".join(str(col) for col in columns) + "\n"
                                    for row in rows:
                                        if isinstance(row, dict):
                                            doc_content += " | ".join(str(row.get(col, "")) for col in columns) + "\n"
                                        elif isinstance(row, list):
                                            doc_content += " | ".join(str(cell) for cell in row) + "\n"
                                        row_count += 1
                            else:
                                # 输出所有列和行
                                doc_content += " | ".join(str(col) for col in columns) + "\n"
                                for row in rows:
                                    if isinstance(row, dict):
                                        doc_content += " | ".join(str(row.get(col, "")) for col in columns) + "\n"
                                    elif isinstance(row, list):
                                        doc_content += " | ".join(str(cell) for cell in row) + "\n"
                                    row_count += 1
            elif doc.structured_data and doc.structured_data.get("rows"):
                # Excel 单 sheet 格式: {columns: [...], rows: [...], ...}
                columns = doc.structured_data.get("columns", [])
                rows = doc.structured_data.get("rows", [])
                if rows and columns:
                    doc_content += f"\n【文档: {doc.filename}，共 {len(rows)} 行】\n"
                    if field_name:
                        target_col = None
                        for col in columns:
                            if field_name.lower() in str(col).lower() or str(col).lower() in field_name.lower():
                                target_col = col
                                break
                        if target_col:
                            doc_content += f"列名: {target_col}\n"
                            for row_idx, row in enumerate(rows):
                                if isinstance(row, dict):
                                    val = row.get(target_col, "")
                                elif isinstance(row, list) and target_col in columns:
                                    val = row[columns.index(target_col)]
                                else:
                                    val = ""
                                doc_content += f"行{row_idx+1}: {val}\n"
                                row_count += 1
                        else:
                            doc_content += " | ".join(str(col) for col in columns) + "\n"
                            for row in rows:
                                if isinstance(row, dict):
                                    doc_content += " | ".join(str(row.get(col, "")) for col in columns) + "\n"
                                elif isinstance(row, list):
                                    doc_content += " | ".join(str(cell) for cell in row) + "\n"
                                row_count += 1
                    else:
                        doc_content += " | ".join(str(col) for col in columns) + "\n"
                        for row in rows:
                            if isinstance(row, dict):
                                doc_content += " | ".join(str(row.get(col, "")) for col in columns) + "\n"
                            elif isinstance(row, list):
                                doc_content += " | ".join(str(cell) for cell in row) + "\n"
                            row_count += 1
            elif doc.structured_data and doc.structured_data.get("tables"):
                # Markdown 表格格式: {tables: [{headers: [...], rows: [...]}]}
                tables = doc.structured_data.get("tables", [])
                for table in tables:
                    if isinstance(table, dict):
                        headers = table.get("headers", [])
                        rows = table.get("rows", [])
                        if rows and headers:
                            doc_content += f"\n【文档: {doc.filename} - 表格】\n"
                            doc_content += " | ".join(str(h) for h in headers) + "\n"
                            for row in rows:
                                if isinstance(row, list):
                                    doc_content += " | ".join(str(cell) for cell in row) + "\n"
                                row_count += 1
                # 如果有标题结构，也添加上下文
                if doc.structured_data.get("titles"):
                    titles = doc.structured_data.get("titles", [])
                    doc_content += f"\n【文档章节结构】\n"
                    for title in titles[:20]:  # 限制前20个标题
                        doc_content += f"{'#' * title.get('level', 1)} {title.get('text', '')}\n"
                # 如果没有提取到表格内容，使用纯文本
                if not doc_content.strip():
                    doc_content = doc.content[:5000] if doc.content else ""
            elif doc.content:
                doc_content = doc.content[:5000]

            if doc_content:
                doc_context = f"【文档: {doc.filename} ({doc.doc_type})】\n{doc_content}"
                logger.info(f"文档 {doc.filename} 上下文长度: {len(doc_context)}, 行数: {row_count}")
                if total_length + len(doc_context) <= max_length:
                    contexts.append(doc_context)
                    total_length += len(doc_context)
                else:
                    remaining = max_length - total_length
                    if remaining > 100:
                        doc_context = doc_context[:remaining] + f"\n...（内容被截断）"
                        contexts.append(doc_context)
                    logger.warning(f"上下文被截断: {doc.filename}, 总长度: {total_length + len(doc_context)}")
                    break

        result = "\n\n".join(contexts) if contexts else "（源文档内容为空）"
        logger.info(f"最终上下文长度: {len(result)}")
        return result

    async def get_template_fields_from_file(
        self,
        file_path: str,
        file_type: str = "xlsx",
        source_contents: List[dict] = None
    ) -> List[TemplateField]:
        """
        从模板文件提取字段定义

        Args:
            file_path: 模板文件路径
            file_type: 文件类型 (xlsx/xls/docx)
            source_contents: 源文档内容列表（用于 AI 生成表头）

        Returns:
            字段列表
        """
        fields = []
        if source_contents is None:
            source_contents = []

        try:
            if file_type in ["xlsx", "xls"]:
                fields = await self._get_template_fields_from_excel(file_type, file_path)
            elif file_type == "docx":
                fields = await self._get_template_fields_from_docx(file_path)

            # 检查是否需要 AI 生成表头
            # 条件：没有字段 OR 所有字段都是自动命名的（如"字段1"、"列1"、"Unnamed"开头）
            needs_ai_generation = (
                len(fields) == 0 or
                all(self._is_auto_generated_field(f.name) for f in fields)
            )

            if needs_ai_generation:
                logger.info(f"模板表头为空或自动生成，尝试 AI 生成表头... (fields={len(fields)}, source_docs={len(source_contents)})")
                ai_fields = await self._generate_fields_with_ai(file_path, file_type, source_contents)
                if ai_fields:
                    fields = ai_fields
                    logger.info(f"AI 生成表头成功: {len(fields)} 个字段")

        except Exception as e:
            logger.error(f"提取模板字段失败: {str(e)}")

        return fields

    def _is_auto_generated_field(self, name: str) -> bool:
        """检查字段名是否是自动生成的（无效表头）"""
        import re
        if not name:
            return True
        name_str = str(name).strip()
        # 匹配 "字段1", "列1", "Field1", "Column1" 等自动生成的名字
        # 或 "Unnamed: 0" 等 Excel 默认名字
        if name_str.startswith('Unnamed'):
            return True
        if re.match(r'^[列字段ColumnField]+\d+$', name_str, re.IGNORECASE):
            return True
        if name_str in ['0', '1', '2'] or name_str.startswith('0.') or name_str.startswith('1.'):
            # 纯数字或类似 "0.1" 的列名
            return True
        return False

    async def _get_template_fields_from_excel(self, file_type: str, file_path: str) -> List[TemplateField]:
        """从 Excel 模板提取字段"""
        fields = []

        try:
            import pandas as pd

            # 尝试读取 Excel 文件
            try:
                # header=0 表示第一行是表头
                df = pd.read_excel(file_path, header=0, nrows=5)
            except Exception as e:
                logger.warning(f"pandas 读取 Excel 表头失败，尝试无表头模式: {e}")
                # 如果失败，尝试不使用表头模式
                df = pd.read_excel(file_path, header=None, nrows=5)
                # 如果没有表头，使用列索引作为列名
                if df.shape[1] > 0:
                    # 检查第一行是否可以作为表头
                    first_row = df.iloc[0].tolist()
                    if all(pd.notna(v) and str(v).strip() != '' for v in first_row):
                        # 第一行有内容，作为表头
                        df.columns = [str(v) if pd.notna(v) else f"列{i}" for i, v in enumerate(first_row)]
                        df = df.iloc[1:]  # 移除表头行
                    else:
                        # 第一行不是有效表头，使用默认列名
                        df.columns = [f"列{i}" for i in range(df.shape[1])]

            logger.info(f"读取 Excel 表头: {df.shape}, 列: {list(df.columns)[:10]}")

            # 如果 DataFrame 列为空或只有默认索引，尝试其他方式
            if len(df.columns) == 0 or (len(df.columns) == 1 and df.columns[0] == 0):
                logger.warning(f"表头解析结果异常，重新解析: {df.columns}")
                # 尝试读取整个文件获取列信息
                df_full = pd.read_excel(file_path, header=None)
                if df_full.shape[1] > 0:
                    # 使用第一行作为列名
                    df = df_full
                    df.columns = [str(v) if pd.notna(v) and str(v).strip() else f"列{i}" for i, v in enumerate(df.iloc[0])]
                    df = df.iloc[1:]

            for idx, col in enumerate(df.columns):
                cell = self._column_to_cell(idx)
                col_str = str(col)
                if col_str == '0' or col_str.startswith('Unnamed'):
                    col_str = f"字段{idx+1}"

                fields.append(TemplateField(
                    cell=cell,
                    name=col_str,
                    field_type=self._infer_field_type_from_value(df[col].iloc[0] if len(df) > 0 else ""),
                    required=True,
                    hint=""
                ))

            logger.info(f"从 Excel 提取到 {len(fields)} 个字段")

        except Exception as e:
            logger.error(f"从Excel提取字段失败: {str(e)}", exc_info=True)

        return fields

    async def _get_template_fields_from_docx(self, file_path: str) -> List[TemplateField]:
        """从 Word 模板提取字段"""
        fields = []

        try:
            from docx import Document

            doc = Document(file_path)

            for table_idx, table in enumerate(doc.tables):
                for row_idx, row in enumerate(table.rows):
                    cells = [cell.text.strip() for cell in row.cells]

                    # 假设第一列是字段名
                    if cells and cells[0]:
                        field_name = cells[0]
                        hint = cells[1] if len(cells) > 1 else ""

                        # 跳过空行或标题行
                        if field_name and field_name not in ["", "字段名", "名称", "项目"]:
                            fields.append(TemplateField(
                                cell=f"T{table_idx}R{row_idx}",
                                name=field_name,
                                field_type=self._infer_field_type_from_hint(hint),
                                required=True,
                                hint=hint
                            ))

        except Exception as e:
            logger.error(f"从Word提取字段失败: {str(e)}")

        return fields

    def _infer_field_type_from_hint(self, hint: str) -> str:
        """从提示词推断字段类型"""
        hint_lower = hint.lower()

        date_keywords = ["年", "月", "日", "日期", "时间", "出生"]
        if any(kw in hint for kw in date_keywords):
            return "date"

        number_keywords = ["数量", "金额", "人数", "面积", "增长", "比率", "%", "率", "总计", "合计"]
        if any(kw in hint_lower for kw in number_keywords):
            return "number"

        return "text"

    def _infer_field_type_from_value(self, value: Any) -> str:
        """从示例值推断字段类型"""
        if value is None or value == "":
            return "text"

        value_str = str(value)

        # 检查日期模式
        import re
        if re.search(r'\d{4}[年/-]\d{1,2}[月/-]\d{1,2}', value_str):
            return "date"

        # 检查数值
        try:
            float(value_str.replace(',', '').replace('%', ''))
            return "number"
        except ValueError:
            pass

        return "text"

    def _column_to_cell(self, col_idx: int) -> str:
        """将列索引转换为单元格列名 (0 -> A, 1 -> B, ...)"""
        result = ""
        while col_idx >= 0:
            result = chr(65 + (col_idx % 26)) + result
            col_idx = col_idx // 26 - 1
        return result

    def _extract_value_from_text(self, text: str, field_name: str) -> str:
        """
        从非 JSON 文本中提取字段值（单值版本）

        Args:
            text: 原始文本
            field_name: 字段名称

        Returns:
            提取的值
        """
        values = self._extract_values_from_text(text, field_name)
        return values[0] if values else ""

    def _extract_values_from_structured_data(self, source_docs: List[SourceDocument], field_name: str) -> List[str]:
        """
        从结构化数据（Excel rows 或 Markdown tables）中直接提取指定列的值

        适用于有 rows 结构的文档数据，无需 LLM 即可提取

        Args:
            source_docs: 源文档列表
            field_name: 字段名称

        Returns:
            值列表，如果无法提取则返回空列表
        """
        all_values = []
        logger.info(f"[_extract_values_from_structured_data] 开始提取字段: {field_name}")
        logger.info(f"  source_docs 数量: {len(source_docs)}")

        for doc_idx, doc in enumerate(source_docs):
            # 尝试从 structured_data 中提取
            structured = doc.structured_data
            logger.info(f"  文档[{doc_idx}]: {doc.filename}, structured类型: {type(structured)}, 是否为空: {not bool(structured)}")
            if structured:
                logger.info(f"    structured_data keys: {list(structured.keys())}")

            if not structured:
                continue

            # 处理多 sheet 格式: {sheets: {sheet_name: {columns, rows}}}
            if structured.get("sheets"):
                sheets = structured.get("sheets", {})
                for sheet_name, sheet_data in sheets.items():
                    if isinstance(sheet_data, dict):
                        columns = sheet_data.get("columns", [])
                        rows = sheet_data.get("rows", [])
                        values = self._extract_column_values(rows, columns, field_name)
                        if values:
                            all_values.extend(values)
                            logger.info(f"从 sheet {sheet_name} 提取到 {len(values)} 个值")
                            break  # 只用第一个匹配的 sheet
                if all_values:
                    break

            # 处理 Markdown 表格格式: {headers: [...], rows: [...], ...}
            elif structured.get("headers") and structured.get("rows"):
                headers = structured.get("headers", [])
                rows = structured.get("rows", [])
                values = self._extract_values_from_markdown_table(headers, rows, field_name)
                if values:
                    all_values.extend(values)
                    logger.info(f"从 Markdown 文档 {doc.filename} 提取到 {len(values)} 个值")
                    break

            # 处理 MongoDB 存储的 tables 格式: {tables: [{headers, rows, ...}, ...]}
            elif structured.get("tables") and isinstance(structured.get("tables"), list):
                tables = structured.get("tables", [])
                logger.info(f"  检测到 tables 格式，共 {len(tables)} 个表")
                for table_idx, table in enumerate(tables):
                    if isinstance(table, dict):
                        headers = table.get("headers", [])
                        rows = table.get("rows", [])
                        logger.info(f"  表格[{table_idx}]: headers={headers[:3]}..., rows数量={len(rows)}")
                        values = self._extract_values_from_markdown_table(headers, rows, field_name)
                        if values:
                            all_values.extend(values)
                            logger.info(f"从表格[{table_idx}] 提取到 {len(values)} 个值")
                            break
                if all_values:
                    break

            # 处理单 sheet 格式: {columns: [...], rows: [...]}
            elif structured.get("rows"):
                columns = structured.get("columns", [])
                rows = structured.get("rows", [])
                values = self._extract_column_values(rows, columns, field_name)
                if values:
                    all_values.extend(values)
                    logger.info(f"从文档 {doc.filename} 提取到 {len(values)} 个值")
                    break

            # 处理 Markdown 表格格式: {tables: [{headers: [...], rows: [...]}]}
            elif structured.get("tables"):
                tables = structured.get("tables", [])
                for table in tables:
                    if isinstance(table, dict):
                        headers = table.get("headers", [])
                        rows = table.get("rows", [])
                        values = self._extract_column_values(rows, headers, field_name)
                        if values:
                            all_values.extend(values)
                            logger.info(f"从 Markdown 表格提取到 {len(values)} 个值")
                            break
                if all_values:
                    break

        return all_values

    def _extract_values_from_markdown_table(self, headers: List, rows: List, field_name: str) -> List[str]:
        """
        从 Markdown 表格中提取指定列的值

        Markdown 表格格式:
        - headers: ["col1", "col2", ...]
        - rows: [["val1", "val2", ...], ...]

        Args:
            headers: 表头列表
            rows: 数据行列表
            field_name: 要提取的字段名

        Returns:
            值列表
        """
        if not rows or not headers:
            logger.warning(f"Markdown 表格为空: headers={headers}, rows={len(rows) if rows else 0}")
            return []

        # 查找匹配的列索引 - 使用增强的匹配算法
        target_idx = self._find_best_matching_column(headers, field_name)

        if target_idx is None:
            logger.warning(f"未找到匹配列: {field_name}, 可用表头: {headers}")
            return []

        logger.info(f"列匹配成功: {field_name} -> {headers[target_idx]} (索引: {target_idx})")

        values = []
        for row in rows:
            if isinstance(row, list) and target_idx < len(row):
                val = row[target_idx]
            else:
                val = ""
            values.append(self._format_value(val))

        return values

    def _find_best_matching_column(self, headers: List, field_name: str) -> Optional[int]:
        """
        查找最佳匹配的列索引

        使用多层匹配策略:
        1. 精确匹配（忽略大小写）
        2. 子字符串匹配（字段名在表头中，或表头在字段名中）
        3. 关键词重叠匹配（中文字符串分割后比对）

        Args:
            headers: 表头列表
            field_name: 要匹配的字段名

        Returns:
            匹配的列索引，找不到返回 None
        """
        field_lower = field_name.lower().strip()
        field_keywords = set(field_lower.replace(" ", "").split())

        best_match_idx = None
        best_match_score = 0

        for idx, header in enumerate(headers):
            header_str = str(header).strip()
            header_lower = header_str.lower()

            # 策略1: 精确匹配（忽略大小写）
            if header_lower == field_lower:
                return idx

            # 策略2: 子字符串匹配
            if field_lower in header_lower or header_lower in field_lower:
                # 计算匹配分数（较长匹配更优先）
                score = max(len(field_lower), len(header_lower)) / min(len(field_lower) + 1, len(header_lower) + 1)
                if score > best_match_score:
                    best_match_score = score
                    best_match_idx = idx
                continue

            # 策略3: 关键词重叠匹配（适用于中文）
            header_keywords = set(header_lower.replace(" ", "").split())
            overlap = field_keywords & header_keywords
            if overlap and len(overlap) > 0:
                score = len(overlap) / max(len(field_keywords), len(header_keywords), 1)
                if score > best_match_score:
                    best_match_score = score
                    best_match_idx = idx

        # 只有当匹配分数超过阈值时才返回
        if best_match_score >= 0.3:
            logger.info(f"模糊匹配: {field_name} -> {headers[best_match_idx]} (分数: {best_match_score:.2f})")
            return best_match_idx

        return None

    def _extract_column_values(self, rows: List, columns: List, field_name: str) -> List[str]:
        """
        从 rows 和 columns 中提取指定列的值

        Args:
            rows: 行数据列表
            columns: 列名列表
            field_name: 要提取的字段名

        Returns:
            值列表
        """
        if not rows or not columns:
            return []

        # 使用增强的匹配算法查找最佳匹配的列索引
        target_idx = self._find_best_matching_column(columns, field_name)

        if target_idx is None:
            logger.warning(f"未找到匹配列: {field_name}, 可用列: {columns}")
            return []

        target_col = columns[target_idx]
        logger.info(f"列匹配成功: {field_name} -> {target_col} (索引: {target_idx})")

        values = []
        for row in rows:
            if isinstance(row, dict):
                val = row.get(target_col, "")
            elif isinstance(row, list) and target_idx < len(row):
                val = row[target_idx]
            else:
                val = ""
            values.append(self._format_value(val))

        return values

    def _format_value(self, val: Any) -> str:
        """
        格式化值为字符串，保持原始格式

        - 如果是浮点数但实际上等于整数，返回整数格式（如 3.0 -> "3"）
        - 如果是浮点数且有小数部分，保留小数（如 3.5 -> "3.5"）
        - 如果是整数，直接返回（如 3 -> "3"）
        - 其他类型直接转为字符串

        Args:
            val: 原始值

        Returns:
            格式化后的字符串
        """
        if val is None:
            return ""

        # 如果已经是字符串
        if isinstance(val, str):
            return val.strip()

        # 如果是布尔值
        if isinstance(val, bool):
            return "true" if val else "false"

        # 如果是数字
        if isinstance(val, (int, float)):
            # 检查是否是浮点数但等于整数
            if isinstance(val, float):
                # 检查是否是小数部分为0
                if val == int(val):
                    return str(int(val))
                else:
                    # 去除尾部多余的0，但保留必要的小数位
                    formatted = f"{val:.10f}".rstrip('0').rstrip('.')
                    return formatted
            else:
                return str(val)

        return str(val)

    def _extract_values_from_json(self, result) -> List[str]:
        """
        从解析后的 JSON 对象/数组中提取值数组

        Args:
            result: json.loads() 返回的对象

        Returns:
            值列表
        """
        if isinstance(result, dict):
            # 优先找 values 数组
            if "values" in result and isinstance(result["values"], list):
                vals = [self._format_value(v).strip() for v in result["values"] if self._format_value(v).strip()]
                if vals:
                    return vals
            # 尝试找 value 字段
            if "value" in result:
                val = self._format_value(result["value"]).strip()
                if val:
                    return [val]
            # 尝试找任何数组类型的键
            for key in result.keys():
                val = result[key]
                if isinstance(val, list) and len(val) > 0:
                    if all(isinstance(v, (str, int, float, bool)) or v is None for v in val):
                        vals = [self._format_value(v).strip() for v in val if v is not None and self._format_value(v).strip()]
                        if vals:
                            return vals
                elif isinstance(val, (str, int, float, bool)):
                    return [self._format_value(val).strip()]
        elif isinstance(result, list):
            vals = [self._format_value(v).strip() for v in result if v is not None and self._format_value(v).strip()]
            if vals:
                return vals
        return []

    def _fix_json(self, json_text: str) -> str:
        """
        尝试修复损坏的 JSON 字符串

        Args:
            json_text: 原始 JSON 文本

        Returns:
            修复后的 JSON 文本，如果无法修复则返回空字符串
        """
        import re

        # 如果以 { 开头，尝试找到配对的 }
        if json_text.startswith('{'):
            # 统计括号深度
            depth = 0
            end_pos = -1
            for i, c in enumerate(json_text):
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break

            if end_pos > 0:
                fixed = json_text[:end_pos]
                logger.info(f"修复 JSON (配对括号): {fixed[:200]}")
                return fixed

            # 如果找不到配对，尝试移除 trailing comma 和其他问题
            # 移除末尾多余的逗号
            fixed = re.sub(r',\s*([}\]])', r'\1', json_text)
            # 确保以 } 结尾
            fixed = fixed.strip()
            if fixed and not fixed.endswith('}') and not fixed.endswith(']'):
                # 尝试补全
                if fixed.startswith('{') and not fixed.endswith('}'):
                    fixed = fixed + '}'
                elif fixed.startswith('[') and not fixed.endswith(']'):
                    fixed = fixed + ']'
            logger.info(f"修复 JSON (正则): {fixed[:200]}")
            return fixed

        # 如果以 [ 开头
        elif json_text.startswith('['):
            depth = 0
            end_pos = -1
            for i, c in enumerate(json_text):
                if c == '[':
                    depth += 1
                elif c == ']':
                    depth -= 1
                    if depth == 0:
                        end_pos = i + 1
                        break

            if end_pos > 0:
                fixed = json_text[:end_pos]
                logger.info(f"修复 JSON (数组配对): {fixed[:200]}")
                return fixed

        return ""

    def _extract_values_by_regex(self, text: str) -> List[str]:
        """
        使用正则从损坏/不完整的 JSON 文本中提取 values 数组

        即使 JSON 被截断，只要能看到 "values": [...] 就能提取

        Args:
            text: 原始文本

        Returns:
            值列表
        """
        import re

        # 方法1: 查找 "values": [ 开始的位置
        values_start = re.search(r'"values"\s*:\s*\[', text)
        if values_start:
            # 从 [ 之后开始提取内容
            start_pos = values_start.end()
            remaining = text[start_pos:]

            # 提取所有被双引号包裹的字符串值
            # 使用简单正则：匹配 "..." 捕获引号内的内容
            values = re.findall(r'"([^"]+)"', remaining)

            if values:
                # 过滤掉空字符串和很短的（可能是键名）
                filtered = [v.strip() for v in values if v.strip() and len(v) > 1]
                if filtered:
                    logger.info(f"正则提取到 {len(filtered)} 个值: {filtered[:3]}")
                    return filtered

        # 方法2: 备选 - 直接查找所有 : "value" 格式的值
        all_strings = re.findall(r':\s*"([^"]{1,200})"', text)
        if all_strings:
            filtered = [s for s in all_strings if s and len(s) < 500]
            if filtered:
                logger.info(f"备选正则提取到 {len(filtered)} 个值: {filtered[:3]}")
                return filtered

        return []

    def _extract_values_from_text(self, text: str, field_name: str) -> List[str]:
        """
        从非 JSON 文本中提取多个字段值

        Args:
            text: 原始文本
            field_name: 字段名称

        Returns:
            提取的值列表
        """
        import re
        import json

        # 先尝试解析整个文本为 JSON，检查是否包含嵌套的 values 数组
        cleaned_text = text.strip()
        # 移除可能的 markdown 代码块标记
        cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()

        try:
            # 尝试解析整个文本为 JSON
            parsed = json.loads(cleaned_text)
            if isinstance(parsed, dict):
                # 如果是 {"values": [...]} 格式，提取 values
                if "values" in parsed and isinstance(parsed["values"], list):
                    return [self._format_value(v).strip() for v in parsed["values"] if self._format_value(v).strip()]
                # 如果是其他 dict 格式，尝试找 values 键
                for key in ["values", "value", "data", "result"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return [self._format_value(v).strip() for v in parsed[key] if self._format_value(v).strip()]
                    elif key in parsed:
                        return [self._format_value(parsed[key]).strip()]
            elif isinstance(parsed, list):
                return [self._format_value(v).strip() for v in parsed if self._format_value(v).strip()]
        except (json.JSONDecodeError, TypeError):
            pass

        # 尝试匹配 JSON 数组格式
        array_match = re.search(r'\[[\s\S]*?\]', text)
        if array_match:
            try:
                arr = json.loads(array_match.group())
                if isinstance(arr, list):
                    # 检查数组元素是否是 {"values": [...]} 结构
                    if arr and isinstance(arr[0], dict) and "values" in arr[0]:
                        # 提取嵌套的 values
                        result = []
                        for item in arr:
                            if isinstance(item, dict) and "values" in item and isinstance(item["values"], list):
                                result.extend([self._format_value(v).strip() for v in item["values"] if self._format_value(v).strip()])
                            elif isinstance(item, dict):
                                result.append(str(item))
                            else:
                                result.append(self._format_value(item))
                        if result:
                            return result
                    return [self._format_value(v).strip() for v in arr if self._format_value(v).strip()]
            except:
                pass

        # 尝试用分号分割（如果文本中有分号分隔的多个值）
        if '；' in text or ';' in text:
            separator = '；' if '；' in text else ';'
            parts = text.split(separator)
            values = []
            for part in parts:
                part = part.strip()
                if part and len(part) < 500:
                    # 清理 Markdown 格式
                    part = re.sub(r'^\*\*|\*\*$', '', part)
                    part = re.sub(r'^\*|\*$', '', part)
                    values.append(part.strip())
            if values:
                return values

        # 尝试多种模式匹配
        patterns = [
            # "字段名: 值" 或 "字段名：值" 格式
            rf'{re.escape(field_name)}[：:]\s*(.+?)(?:\n|$)',
            # "值" 在引号中
            rf'"value"\s*:\s*"([^"]+)"',
            # "值" 在单引号中
            rf"['\"]?value['\"]?\s*:\s*['\"]([^'\"]+)['\"]",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                value = match.group(1).strip()
                # 清理 Markdown 格式
                value = re.sub(r'^\*\*|\*\*$', '', value)
                value = re.sub(r'^\*|\*$', '', value)
                value = value.strip()
                if value and len(value) < 1000:
                    return [value]

        # 如果无法匹配，返回原始内容
        content = text.strip()[:500] if text.strip() else ""
        return [content] if content else []

    async def _analyze_unstructured_docs_for_fields(
        self,
        source_docs: List[SourceDocument],
        field: TemplateField,
        user_hint: Optional[str] = None
    ) -> Optional[FillResult]:
        """
        对非结构化文档进行 AI 分析，尝试提取结构化数据

        适用于 Markdown 等没有表格格式的文档，通过 AI 分析提取结构化信息

        Args:
            source_docs: 源文档列表
            field: 字段定义
            user_hint: 用户提示

        Returns:
            FillResult 如果提取成功，否则返回 None
        """
        # 找出非结构化的 Markdown/TXT 文档（没有表格的）
        unstructured_docs = []
        for doc in source_docs:
            if doc.doc_type in ["md", "txt", "markdown"]:
                # 检查是否有表格
                has_tables = (
                    doc.structured_data and
                    doc.structured_data.get("tables") and
                    len(doc.structured_data.get("tables", [])) > 0
                )
                if not has_tables:
                    unstructured_docs.append(doc)

        if not unstructured_docs:
            return None

        logger.info(f"发现 {len(unstructured_docs)} 个非结构化文档，尝试 AI 分析...")

        # 对每个非结构化文档进行 AI 分析
        for doc in unstructured_docs:
            try:
                # 使用 markdown_ai_service 的 statistics 分析类型
                # 这种类型专门用于政府统计公报等包含数据的文档
                hint_text = field.hint if field.hint else f"请提取{field.name}的信息"
                if user_hint:
                    hint_text = f"{user_hint}。{hint_text}"

                # 构建针对字段提取的提示词
                prompt = f"""你是一个专业的数据提取专家。请从以下文档内容中提取与"{field.name}"完全匹配的数据。

【重要】字段名: "{field.name}"
【重要】字段提示: {hint_text}

请严格按照以下步骤操作：
1. 在文档中搜索与"{field.name}"完全相同或高度相关的关键词
2. 找到后，提取该关键词后的数值（注意：只要数值，不要单位）
3. 如果是表格中的数据，直接提取该单元格的数值
4. 如果是段落描述，在关键词附近找数值

【重要】返回值规则：
- 只返回纯数值，不要单位（如 "4.9" 而不是 "4.9万亿元"）
- 如果原文是"4.9万亿元"，返回 "4.9"
- 如果原文是"144000万册"，返回 "144000"
- 如果是百分比如"增长7.7%"，返回 "7.7"
- 如果没有找到完全匹配的数据，返回空数组

文档内容：
{doc.content[:10000] if doc.content else ""}

请用严格的 JSON 格式返回：
{{
    "values": ["值1", "值2", ...],  // 只填数值，不要单位
    "source": "数据来源说明",
    "confidence": 0.0到1.0之间的置信度
}}

示例：
- 如果字段是"图书馆总藏量（万册）"且文档说"图书总藏量14.4亿册"，返回 values: ["144000"]
- 如果字段是"国内旅游收入（亿元）"且文档说"国内旅游收入4.9万亿元"，返回 values: ["49000"]"""

                messages = [
                    {"role": "system", "content": "你是一个专业的数据提取助手，擅长从政府统计公报等文档中提取数据。请严格按JSON格式输出。"},
                    {"role": "user", "content": prompt}
                ]

                response = await self.llm.chat(
                    messages=messages,
                    temperature=0.1,
                    max_tokens=4000
                )

                content = self.llm.extract_message_content(response)
                logger.info(f"AI 分析返回: {content[:500]}")

                # 解析 JSON
                import json
                import re

                # 清理 markdown 格式
                cleaned = content.strip()
                cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
                cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
                cleaned = cleaned.strip()

                # 查找 JSON
                json_start = -1
                for i, c in enumerate(cleaned):
                    if c == '{' or c == '[':
                        json_start = i
                        break

                if json_start == -1:
                    continue

                json_text = cleaned[json_start:]
                try:
                    result = json.loads(json_text)
                    values = self._extract_values_from_json(result)
                    if values:
                        return FillResult(
                            field=field.name,
                            values=values,
                            value=values[0] if values else "",
                            source=f"AI分析: {doc.filename}",
                            confidence=result.get("confidence", 0.8)
                        )
                except json.JSONDecodeError:
                    # 尝试修复 JSON
                    fixed = self._fix_json(json_text)
                    if fixed:
                        try:
                            result = json.loads(fixed)
                            values = self._extract_values_from_json(result)
                            if values:
                                return FillResult(
                                    field=field.name,
                                    values=values,
                                    value=values[0] if values else "",
                                    source=f"AI分析: {doc.filename}",
                                    confidence=result.get("confidence", 0.8)
                                )
                        except json.JSONDecodeError:
                            pass

            except Exception as e:
                logger.warning(f"AI 分析文档 {doc.filename} 失败: {str(e)}")
                continue

        return None

    async def _generate_fields_with_ai(
        self,
        file_path: str,
        file_type: str,
        source_contents: List[dict] = None
    ) -> Optional[List[TemplateField]]:
        """
        使用 AI 为空表生成表头字段

        当模板文件为空或没有表头时，调用 AI 分析并生成合适的字段名

        Args:
            file_path: 模板文件路径
            file_type: 文件类型

        Returns:
            生成的字段列表，如果失败返回 None
        """
        try:
            import pandas as pd

            # 读取 Excel 内容检查是否为空
            if file_type in ["xlsx", "xls"]:
                df = pd.read_excel(file_path, header=None)
                if df.shape[0] == 0 or df.shape[1] == 0:
                    logger.info("Excel 表格为空")
                    # 生成默认字段
                    return [TemplateField(
                        cell=self._column_to_cell(i),
                        name=f"字段{i+1}",
                        field_type="text",
                        required=False,
                        hint="请填写此字段"
                    ) for i in range(5)]

                # 表格有数据但没有表头
                if df.shape[1] > 0:
                    # 读取第一行作为参考，看是否为空
                    first_row = df.iloc[0].tolist() if len(df) > 0 else []
                    if not any(pd.notna(v) and str(v).strip() != '' for v in first_row):
                        # 第一行为空，AI 生成表头
                        content_sample = df.iloc[:10].to_string() if len(df) >= 10 else df.to_string()
                    else:
                        content_sample = df.to_string()
                else:
                    content_sample = ""

            # 调用 AI 生成表头
            # 根据源文档内容生成表头
            source_info = ""
            logger.info(f"[DEBUG] _generate_fields_with_ai received source_contents: {len(source_contents) if source_contents else 0} items")
            if source_contents:
                for sc in source_contents:
                    logger.info(f"[DEBUG]   source doc: filename={sc.get('filename')}, content_len={len(sc.get('content', ''))}, titles={len(sc.get('titles', []))}, tables_count={sc.get('tables_count', 0)}, has_tables_summary={bool(sc.get('tables_summary'))}")
                source_info = "\n\n【源文档内容摘要】（根据以下文档内容生成表头）：\n"
                for idx, src in enumerate(source_contents[:5]):  # 最多5个源文档
                    filename = src.get("filename", f"文档{idx+1}")
                    doc_type = src.get("doc_type", "unknown")
                    content = src.get("content", "")[:3000]  # 限制内容长度
                    titles = src.get("titles", [])[:10]  # 最多10个标题
                    tables_count = src.get("tables_count", 0)
                    tables_summary = src.get("tables_summary", "")

                    source_info += f"\n--- 文档 {idx+1}: {filename} ({doc_type}) ---\n"
                    # 处理 titles（可能是字符串列表或字典列表）
                    if titles:
                        title_texts = []
                        for t in titles[:5]:
                            if isinstance(t, dict):
                                title_texts.append(t.get('text', ''))
                            else:
                                title_texts.append(str(t))
                        if title_texts:
                            source_info += f"【章节标题】: {', '.join(title_texts)}\n"
                    if tables_count > 0:
                        source_info += f"【包含表格数】: {tables_count}\n"
                    if tables_summary:
                        source_info += f"{tables_summary}\n"
                    elif content:
                        source_info += f"【内容预览】: {content[:1500]}...\n"

            prompt = f"""你是一个专业的表格设计助手。请根据源文档内容生成合适的表格表头字段。

任务：用户有一些源文档（可能包含表格数据、统计信息等），需要填写到表格中。请分析源文档内容，生成适合的表头字段。

{source_info}

请生成5-10个简洁的表头字段名，这些字段应该：
1. 简洁明了，易于理解
2. 适合作为表格列标题
3. 直接对应源文档中的关键数据项
4. 字段之间有明显的区分度

请严格按照以下 JSON 格式输出（只需输出 JSON，不要其他内容）：
{{
    "fields": [
        {{"name": "字段名1", "hint": "字段说明提示1"}},
        {{"name": "字段名2", "hint": "字段说明提示2"}}
    ]
}}
"""
            messages = [
                {"role": "system", "content": "你是一个专业的表格设计助手。请严格按JSON格式输出。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )

            content = self.llm.extract_message_content(response)
            logger.info(f"AI 生成表头返回: {content[:500]}")

            # 解析 JSON
            import json
            import re

            # 清理 markdown 格式
            cleaned = content.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            # 查找 JSON
            json_start = -1
            for i, c in enumerate(cleaned):
                if c == '{':
                    json_start = i
                    break

            if json_start == -1:
                logger.warning("无法找到 JSON 开始位置")
                return None

            json_text = cleaned[json_start:]
            result = json.loads(json_text)

            if result and "fields" in result:
                fields = []
                for idx, f in enumerate(result["fields"]):
                    fields.append(TemplateField(
                        cell=self._column_to_cell(idx),
                        name=f.get("name", f"字段{idx+1}"),
                        field_type="text",
                        required=False,
                        hint=f.get("hint", "")
                    ))
                return fields

        except Exception as e:
            logger.error(f"AI 生成表头失败: {str(e)}")

        return None


# ==================== 全局单例 ====================

template_fill_service = TemplateFillService()
