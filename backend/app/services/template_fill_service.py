"""
表格模板填写服务

从非结构化文档中检索信息并填写到表格模板
"""
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.database import mongodb
from app.services.llm_service import llm_service
from app.core.document_parser import ParserFactory

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
    ai_structured_data: Optional[Dict[str, Any]] = None  # AI 结构化分析结果缓存


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
        user_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        填写表格模板

        Args:
            template_fields: 模板字段列表
            source_doc_ids: 源文档 MongoDB ID 列表
            source_file_paths: 源文档文件路径列表
            user_hint: 用户提示（如"请从合同文档中提取"）

        Returns:
            填写结果
        """
        filled_data = {}
        fill_details = []

        logger.info(f"开始填表: {len(template_fields)} 个字段, {len(source_doc_ids or [])} 个源文档, {len(source_file_paths or [])} 个文件路径")

        # 1. 加载源文档内容
        source_docs = await self._load_source_documents(source_doc_ids, source_file_paths)

        logger.info(f"加载了 {len(source_docs)} 个源文档")
        for doc in source_docs:
            logger.info(f"  - 文档: {doc.filename}, 类型: {doc.doc_type}, 内容长度: {len(doc.content)}, AI分析: {bool(doc.ai_structured_data)}")

        if not source_docs:
            logger.warning("没有找到源文档，填表结果将全部为空")

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
        加载源文档内容，并对 TXT 文件进行 AI 结构化分析

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
                        doc_type = doc.get("doc_type", "unknown")
                        content = doc.get("content", "")

                        # 对 TXT 文档进行 AI 结构化分析
                        ai_structured = None
                        if doc_type == "txt" and content:
                            logger.info(f"MongoDB TXT 文档需要 AI 分析: {doc_id}, 内容长度: {len(content)}")
                            ai_structured = await self._analyze_txt_once(content, doc.get("metadata", {}).get("original_filename", "unknown"))
                            logger.info(f"AI 分析结果: has_data={ai_structured is not None}")

                        source_docs.append(SourceDocument(
                            doc_id=doc_id,
                            filename=doc.get("metadata", {}).get("original_filename", "unknown"),
                            doc_type=doc_type,
                            content=content,
                            structured_data=doc.get("structured_data", {}),
                            ai_structured_data=ai_structured
                        ))
                        logger.info(f"从MongoDB加载文档: {doc_id}")
                except Exception as e:
                    logger.error(f"从MongoDB加载文档失败 {doc_id}: {str(e)}")

        # 2. 从文件路径加载文档
        if source_file_paths:
            logger.info(f"开始从文件路径加载 {len(source_file_paths)} 个文档")
            for file_path in source_file_paths:
                try:
                    logger.info(f"  加载文件: {file_path}")
                    parser = ParserFactory.get_parser(file_path)
                    result = parser.parse(file_path)
                    logger.info(f"  解析结果: success={result.success}, error={result.error}")
                    if result.success:
                        # result.data 的结构取决于解析器类型:
                        # - Excel 单 sheet: {columns: [...], rows: [...], row_count, column_count}
                        # - Excel 多 sheet: {sheets: {sheet_name: {columns, rows, ...}}}
                        # - Word/TXT: {content: "...", structured_data: {...}}
                        doc_data = result.data if result.data else {}
                        doc_content = doc_data.get("content", "") if isinstance(doc_data, dict) else ""
                        doc_structured = doc_data if isinstance(doc_data, dict) and "rows" in doc_data or isinstance(doc_data, dict) and "sheets" in doc_data else {}
                        doc_type = result.metadata.get("extension", "unknown").replace(".", "").lower()
                        logger.info(f"  文件类型: {doc_type}, 内容长度: {len(doc_content)}")

                        # 对 TXT 文件进行 AI 结构化分析
                        ai_structured = None
                        if doc_type == "txt" and doc_content:
                            logger.info(f"  检测到 TXT 文件，内容前100字: {doc_content[:100]}")
                            ai_structured = await self._analyze_txt_once(doc_content, result.metadata.get("filename", Path(file_path).name))
                            logger.info(f"  AI 分析完成: has_result={ai_structured is not None}")
                            if ai_structured:
                                logger.info(f"  AI 结果 keys: {list(ai_structured.keys())}")
                                if "table" in ai_structured:
                                    table = ai_structured.get("table", {})
                                    logger.info(f"  AI 表格: {len(table.get('columns', []))} 列, {len(table.get('rows', []))} 行")

                        source_docs.append(SourceDocument(
                            doc_id=file_path,
                            filename=result.metadata.get("filename", Path(file_path).name),
                            doc_type=doc_type,
                            content=doc_content,
                            structured_data=doc_structured,
                            ai_structured_data=ai_structured
                        ))
                    else:
                        logger.warning(f"文档解析失败 {file_path}: {result.error}")
                except Exception as e:
                    logger.error(f"从文件加载文档失败 {file_path}: {str(e)}", exc_info=True)

        return source_docs

    async def _analyze_txt_once(self, content: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        对 TXT 内容进行一次性 AI 分析，提取保持行结构的表格数据

        Args:
            content: 原始文本内容
            filename: 文件名

        Returns:
            分析结果字典，包含表格数据
        """
        # 确保 content 是字符串
        if isinstance(content, bytes):
            try:
                content = content.decode('utf-8')
            except:
                content = content.decode('gbk', errors='replace')

        if not content or len(str(content).strip()) < 10:
            logger.warning(f"TXT 内容过短或为空: {filename}, 类型: {type(content)}")
            return None

        content = str(content)

        # 限制内容长度，避免 token 超限
        max_chars = 8000
        truncated_content = content[:max_chars] if len(content) > max_chars else content

        prompt = f"""你是一个专业的数据提取助手。请从以下文本内容中提取表格数据。

文件名：{filename}

文本内容：
{truncated_content}

请仔细分析文本中的表格数据，提取所有行。每行是一个完整的数据记录。

请严格按以下 JSON 格式输出，不要添加任何解释：
{{
    "table": {{
        "columns": ["列1", "列2", "列3", ...],
        "rows": [
            ["值1", "值2", "值3", ...],
            ["值1", "值2", "值3", ...]
        ]
    }},
    "summary": "简要说明数据内容"
}}"""

        messages = [
            {"role": "system", "content": "你是一个专业的数据提取助手。请严格按JSON格式输出，只输出纯JSON。"},
            {"role": "user", "content": prompt}
        ]

        try:
            logger.info(f"开始 AI 分析 TXT 文件: {filename}, 内容长度: {len(truncated_content)}")
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )

            ai_content = self.llm.extract_message_content(response)
            logger.info(f"LLM 返回内容长度: {len(ai_content)}, 内容前200字: {ai_content[:200]}")

            # 解析 JSON
            import json
            import re

            cleaned = ai_content.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            logger.info(f"清理后内容前200字: {cleaned[:200]}")

            # 查找 JSON
            json_start = cleaned.find('{')
            json_end = cleaned.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = cleaned[json_start:json_end]
                logger.info(f"提取的JSON字符串: {json_str[:200]}")
                try:
                    result = json.loads(json_str)
                    # 兼容不同格式的返回
                    if "table" in result:
                        table = result["table"]
                    elif "data" in result:
                        table = result["data"]
                    elif "rows" in result:
                        table = {"columns": result.get("columns", []), "rows": result.get("rows", [])}
                    else:
                        # 尝试直接使用根级别的数据
                        table = result

                    if isinstance(table, dict) and ("columns" in table or "rows" in table):
                        columns = table.get("columns", [])
                        rows = table.get("rows", [])
                        logger.info(f"TXT AI 分析成功: {filename}, 列数: {len(columns)}, 行数: {len(rows)}")
                        return {"table": {"columns": columns, "rows": rows}, "summary": result.get("summary", "")}
                    else:
                        logger.warning(f"JSON 中没有找到有效的表格数据: {filename}, result keys: {list(result.keys())}")
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON 解析失败: {e}, json_str: {json_str[:200]}")

            logger.warning(f"无法解析 AI 返回的 JSON: {filename}, ai_content: {ai_content[:500]}")
            return None

        except Exception as e:
            logger.error(f"AI 分析 TXT 失败: {str(e)}, 文件: {filename}", exc_info=True)
            return None

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

        # 无法从结构化数据提取，使用 LLM
        logger.info(f"字段 {field.name} 无法直接从结构化数据提取，使用 LLM...")

        # 构建上下文文本 - 传入字段名，只提取该列数据
        context_text = await self._build_context_text(source_docs, field_name=field.name, max_length=6000)

        # 构建提示词
        hint_text = field.hint if field.hint else f"请提取{field.name}的信息"
        if user_hint:
            hint_text = f"{user_hint}。{hint_text}"

        prompt = f"""你是一个专业的数据提取专家。请从以下文档内容中提取"{field.name}"字段的值。

参考文档内容：
{context_text}

请仔细阅读上述内容，找到所有与"{field.name}"相关的值。
如果内容是表格格式，请找到对应的列，提取该列所有行的值。
每一行对应数组中的一个元素，保持行与行的对应关系。
如果找不到对应的值，返回空数组。

请严格按以下JSON格式输出（只输出纯JSON，不要任何解释）：
{{"values": ["值1", "值2", "值3", ...], "source": "来源说明", "confidence": 0.9}}
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
                max_tokens=2000
            )

            content = self.llm.extract_message_content(response)

            # 解析 JSON 响应
            import json
            import re

            extracted_values = []
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

    async def _build_context_text(self, source_docs: List[SourceDocument], field_name: str = None, max_length: int = 8000) -> str:
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
            elif doc.content:
                # TXT 文件优先使用 AI 分析后的结构化数据
                if doc.doc_type == "txt" and doc.ai_structured_data:
                    # 使用 AI 结构化分析结果
                    ai_table = doc.ai_structured_data.get("table", {})
                    columns = ai_table.get("columns", [])
                    rows = ai_table.get("rows", [])

                    logger.info(f"TXT AI 结构化数据: doc_type={doc.doc_type}, has_ai_data={doc.ai_structured_data is not None}, columns={columns}, rows={len(rows) if rows else 0}")

                    if columns and rows:
                        doc_content += f"\n【文档: {doc.filename} - AI 结构化表格，共 {len(rows)} 行】\n"
                        if field_name:
                            # 查找匹配的列
                            target_col = None
                            for col in columns:
                                if field_name.lower() in str(col).lower() or str(col).lower() in field_name.lower():
                                    target_col = col
                                    break
                            if target_col:
                                doc_content += f"列名: {target_col}\n"
                                for row_idx, row in enumerate(rows):
                                    if isinstance(row, list) and target_col in columns:
                                        val = row[columns.index(target_col)]
                                    else:
                                        val = str(row.get(target_col, "")) if isinstance(row, dict) else ""
                                    doc_content += f"行{row_idx+1}: {val}\n"
                                    row_count += 1
                        else:
                            # 输出表格
                            doc_content += " | ".join(str(col) for col in columns) + "\n"
                            for row in rows:
                                if isinstance(row, list):
                                    doc_content += " | ".join(str(cell) for cell in row) + "\n"
                                else:
                                    doc_content += " | ".join(str(row.get(col, "")) for col in columns) + "\n"
                                row_count += 1
                        logger.info(f"使用 TXT AI 结构化表格: {doc.filename}, {len(columns)} 列, {len(rows)} 行")
                    else:
                        # AI 结果无表格，回退到原始内容
                        doc_content = doc.content[:8000]
                        logger.warning(f"TXT AI 结果无表格: {doc.filename}, 使用原始内容")
                elif doc.doc_type == "txt" and doc.content:
                    # 没有 AI 分析结果，直接使用原始内容
                    doc_content = doc.content[:8000]
                    logger.info(f"使用 TXT 原始内容: {doc.filename}, 长度: {len(doc_content)}")
                else:
                    # 其他文档类型直接使用内容
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

    async def analyze_txt_with_ai(self, content: str, filename: str = "") -> Dict[str, Any]:
        """
        使用 AI 分析 TXT 文本内容，提取结构化数据

        Args:
            content: 原始文本内容
            filename: 文件名（用于日志）

        Returns:
            结构化数据，包含:
            - key_value_pairs: 键值对列表
            - tables: 表格数据列表
            - numeric_data: 数值数据列表
            - text_summary: 文本摘要
        """
        if not content or len(content.strip()) < 10:
            logger.warning(f"TXT 内容过短或为空，跳过 AI 分析: {filename}")
            return {}

        # 截断过长的文本，避免 token 超限
        max_chars = 15000
        truncated_content = content[:max_chars] if len(content) > max_chars else content

        system_prompt = """你是一个专业的数据提取专家。请分析提供的文本内容，提取其中包含的结构化信息。

请提取以下类型的数据：

1. **键值对信息**：从文本中提取的名词-值对，如"姓名: 张三"、"年龄: 25"等
2. **表格数据**：如果文本中包含表格或列表形式的数据，提取出来
3. **数值数据**：包含数值、金额、百分比、统计数字等
4. **关键描述**：文本的核心内容摘要

请严格按照以下 JSON 格式输出，不要添加任何 Markdown 标记或解释：
{
    "key_value_pairs": [
        {"key": "键名1", "value": "值1"},
        {"key": "键名2", "value": "值2"}
    ],
    "tables": [
        {
            "description": "表格描述",
            "columns": ["列1", "列2"],
            "rows": [["值1", "值2"], ["值3", "值4"]]
        }
    ],
    "numeric_data": [
        {"name": "数据项名称", "value": 123.45, "unit": "单位"}
    ],
    "text_summary": "一段简洁的文本摘要，不超过200字"
}"""

        user_message = f"""请分析以下文本内容，提取结构化数据：

文件名：{filename}

文本内容：
{truncated_content}

请严格按 JSON 格式输出。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            logger.info(f"开始 AI 分析 TXT 文件: {filename}, 内容长度: {len(truncated_content)}")
            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=2000
            )

            ai_content = self.llm.extract_message_content(response)
            logger.info(f"AI 返回内容长度: {len(ai_content)}")

            # 解析 JSON
            import json
            import re

            # 清理 markdown 格式
            cleaned = ai_content.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
            cleaned = cleaned.strip()

            # 提取 JSON
            json_start = -1
            for i, c in enumerate(cleaned):
                if c == '{':
                    json_start = i
                    break

            if json_start >= 0:
                brace_count = 0
                json_end = -1
                for i in range(json_start, len(cleaned)):
                    if cleaned[i] == '{':
                        brace_count += 1
                    elif cleaned[i] == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break

                if json_end > json_start:
                    json_str = cleaned[json_start:json_end]
                    result = json.loads(json_str)
                    logger.info(f"TXT AI 分析成功: {filename}, 提取到 {len(result.get('key_value_pairs', []))} 个键值对")
                    return result

            logger.warning(f"无法从 AI 返回中解析 JSON: {filename}")
            return {}

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}, 文件: {filename}")
            return {}
        except Exception as e:
            logger.error(f"AI 分析 TXT 失败: {str(e)}, 文件: {filename}", exc_info=True)
            return {}

    def _format_structured_for_context(self, structured_data: Dict[str, Any], filename: str) -> str:
        """
        将结构化数据格式化为上下文文本

        Args:
            structured_data: AI 分析返回的结构化数据
            filename: 文件名

        Returns:
            格式化的文本上下文
        """
        parts = []

        # 添加标题
        parts.append(f"【文档: {filename} - AI 结构化分析结果】")

        # 格式化键值对
        key_value_pairs = structured_data.get("key_value_pairs", [])
        if key_value_pairs:
            parts.append("\n## 关键信息：")
            for kv in key_value_pairs[:20]:  # 最多 20 个
                parts.append(f"- {kv.get('key', '')}: {kv.get('value', '')}")

        # 格式化表格数据
        tables = structured_data.get("tables", [])
        if tables:
            parts.append("\n## 表格数据：")
            for i, table in enumerate(tables[:5]):  # 最多 5 个表格
                desc = table.get("description", f"表格{i+1}")
                columns = table.get("columns", [])
                rows = table.get("rows", [])
                if columns and rows:
                    parts.append(f"\n### {desc}")
                    parts.append("| " + " | ".join(str(c) for c in columns) + " |")
                    parts.append("| " + " | ".join(["---"] * len(columns)) + " |")
                    for row in rows[:10]:  # 每个表格最多 10 行
                        parts.append("| " + " | ".join(str(cell) for cell in row) + " |")

        # 格式化数值数据
        numeric_data = structured_data.get("numeric_data", [])
        if numeric_data:
            parts.append("\n## 数值数据：")
            for num in numeric_data[:15]:  # 最多 15 个
                name = num.get("name", "")
                value = num.get("value", "")
                unit = num.get("unit", "")
                parts.append(f"- {name}: {value} {unit}")

        # 添加文本摘要
        text_summary = structured_data.get("text_summary", "")
        if text_summary:
            parts.append(f"\n## 内容摘要：\n{text_summary}")

        return "\n".join(parts)

    async def get_template_fields_from_file(
        self,
        file_path: str,
        file_type: str = "xlsx"
    ) -> List[TemplateField]:
        """
        从模板文件提取字段定义

        Args:
            file_path: 模板文件路径
            file_type: 文件类型 (xlsx/xls/docx)

        Returns:
            字段列表
        """
        fields = []

        try:
            if file_type in ["xlsx", "xls"]:
                fields = await self._get_template_fields_from_excel(file_path)
            elif file_type == "docx":
                fields = await self._get_template_fields_from_docx(file_path)

        except Exception as e:
            logger.error(f"提取模板字段失败: {str(e)}")

        return fields

    async def _get_template_fields_from_excel(self, file_path: str) -> List[TemplateField]:
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
        从结构化数据（Excel rows）或 AI 结构化分析结果中直接提取指定列的值

        适用于有 rows 结构的文档数据，无需 LLM 即可提取

        Args:
            source_docs: 源文档列表
            field_name: 字段名称

        Returns:
            值列表，如果无法提取则返回空列表
        """
        all_values = []

        for doc in source_docs:
            # 优先从 AI 结构化数据中提取（适用于 TXT 文件）
            if doc.ai_structured_data:
                ai_table = doc.ai_structured_data.get("table", {})
                columns = ai_table.get("columns", [])
                rows = ai_table.get("rows", [])
                if columns and rows:
                    values = self._extract_column_values(rows, columns, field_name)
                    if values:
                        all_values.extend(values)
                        logger.info(f"从 TXT AI 结构化数据提取到 {len(values)} 个值: {doc.filename}")
                        break

            # 尝试从 structured_data 中提取
            structured = doc.structured_data

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

            # 处理单 sheet 格式: {columns: [...], rows: [...]}
            elif structured.get("rows"):
                columns = structured.get("columns", [])
                rows = structured.get("rows", [])
                values = self._extract_column_values(rows, columns, field_name)
                if values:
                    all_values.extend(values)
                    logger.info(f"从文档 {doc.filename} 提取到 {len(values)} 个值")
                    break

        return all_values

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

        # 查找匹配的列（模糊匹配）
        target_col = None
        for col in columns:
            col_str = str(col)
            if field_name.lower() in col_str.lower() or col_str.lower() in field_name.lower():
                target_col = col
                break

        if not target_col:
            logger.warning(f"未找到匹配列: {field_name}, 可用列: {columns}")
            return []

        values = []
        for row in rows:
            if isinstance(row, dict):
                val = row.get(target_col, "")
            elif isinstance(row, list) and target_col in columns:
                val = row[columns.index(target_col)]
            else:
                val = ""
            values.append(str(val) if val is not None else "")

        return values

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
                vals = [str(v).strip() for v in result["values"] if v and str(v).strip()]
                if vals:
                    return vals
            # 尝试找 value 字段
            if "value" in result:
                val = str(result["value"]).strip()
                if val:
                    return [val]
            # 尝试找任何数组类型的键
            for key in result.keys():
                val = result[key]
                if isinstance(val, list) and len(val) > 0:
                    if all(isinstance(v, (str, int, float, bool)) or v is None for v in val):
                        vals = [str(v).strip() for v in val if v is not None and str(v).strip()]
                        if vals:
                            return vals
                elif isinstance(val, (str, int, float, bool)):
                    return [str(val).strip()]
        elif isinstance(result, list):
            vals = [str(v).strip() for v in result if v is not None and str(v).strip()]
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
                    return [str(v).strip() for v in parsed["values"] if v and str(v).strip()]
                # 如果是其他 dict 格式，尝试找 values 键
                for key in ["values", "value", "data", "result"]:
                    if key in parsed and isinstance(parsed[key], list):
                        return [str(v).strip() for v in parsed[key] if v and str(v).strip()]
                    elif key in parsed:
                        return [str(parsed[key]).strip()]
            elif isinstance(parsed, list):
                return [str(v).strip() for v in parsed if v and str(v).strip()]
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
                                result.extend([str(v).strip() for v in item["values"] if v and str(v).strip()])
                            elif isinstance(item, dict):
                                result.append(str(item))
                            else:
                                result.append(str(item))
                        if result:
                            return result
                    return [str(v).strip() for v in arr if v and str(v).strip()]
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


# ==================== 全局单例 ====================

template_fill_service = TemplateFillService()
