"""
Word 文档 AI 解析服务

使用 LLM (GLM) 对 Word 文档进行深度理解，提取结构化数据
"""
import logging
from typing import Dict, Any, List, Optional
import json

from app.services.llm_service import llm_service
from app.services.visualization_service import visualization_service
from app.core.document_parser.docx_parser import DocxParser

logger = logging.getLogger(__name__)


class WordAIService:
    """Word 文档 AI 解析服务"""

    def __init__(self):
        self.llm = llm_service
        self.parser = DocxParser()

    async def parse_word_with_ai(
        self,
        file_path: str,
        user_hint: str = ""
    ) -> Dict[str, Any]:
        """
        使用 AI 解析 Word 文档，提取结构化数据

        适用于从非结构化的 Word 文档中提取表格数据、键值对等信息

        Args:
            file_path: Word 文件路径
            user_hint: 用户提示词，指定要提取的内容类型

        Returns:
            Dict: 包含结构化数据的解析结果
        """
        try:
            # 1. 先用基础解析器提取原始内容
            parse_result = self.parser.parse(file_path)

            if not parse_result.success:
                return {
                    "success": False,
                    "error": parse_result.error,
                    "structured_data": None
                }

            # 2. 获取原始数据
            raw_data = parse_result.data
            paragraphs = raw_data.get("paragraphs", [])
            paragraphs_with_style = raw_data.get("paragraphs_with_style", [])
            tables = raw_data.get("tables", [])
            content = raw_data.get("content", "")
            images_info = raw_data.get("images", {})
            metadata = parse_result.metadata or {}

            image_count = images_info.get("image_count", 0)
            image_descriptions = images_info.get("descriptions", [])

            logger.info(f"Word 基础解析完成: {len(paragraphs)} 个段落, {len(tables)} 个表格, {image_count} 张图片")

            # 3. 提取图片数据（用于视觉分析）
            images_base64 = []
            if image_count > 0:
                try:
                    images_base64 = self.parser.extract_images_as_base64(file_path)
                    logger.info(f"提取到 {len(images_base64)} 张图片的 base64 数据")
                except Exception as e:
                    logger.warning(f"提取图片 base64 失败: {str(e)}")

            # 4. 根据内容类型选择 AI 解析策略
            # 如果有图片，先分析图片
            image_analysis = ""
            if images_base64:
                image_analysis = await self._analyze_images_with_ai(images_base64, user_hint)
                logger.info(f"图片 AI 分析完成: {len(image_analysis)} 字符")

            # 优先处理：表格 > (表格+文本) > 纯文本
            if tables and len(tables) > 0:
                structured_data = await self._extract_tables_with_ai(
                    tables, paragraphs, image_count, user_hint, metadata, image_analysis
                )
            elif paragraphs and len(paragraphs) > 0:
                structured_data = await self._extract_from_text_with_ai(
                    paragraphs, content, image_count, image_descriptions, user_hint, image_analysis
                )
            else:
                structured_data = {
                    "success": True,
                    "type": "empty",
                    "message": "文档内容为空"
                }

            # 添加图片分析结果
            if image_analysis:
                structured_data["image_analysis"] = image_analysis

            return structured_data

        except Exception as e:
            logger.error(f"AI 解析 Word 文档失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "structured_data": None
            }

    async def _extract_tables_with_ai(
        self,
        tables: List[Dict],
        paragraphs: List[str],
        image_count: int,
        user_hint: str,
        metadata: Dict,
        image_analysis: str = ""
    ) -> Dict[str, Any]:
        """
        使用 AI 从 Word 表格和文本中提取结构化数据

        Args:
            tables: 表格列表
            paragraphs: 段落列表
            image_count: 图片数量
            user_hint: 用户提示
            metadata: 文档元数据
            image_analysis: 图片 AI 分析结果

        Returns:
            结构化数据
        """
        try:
            # 构建表格文本描述
            tables_text = self._build_tables_description(tables)

            # 构建段落描述
            paragraphs_text = "\n".join(paragraphs[:50]) if paragraphs else "（无正文文本）"
            if len(paragraphs) > 50:
                paragraphs_text += f"\n...（共 {len(paragraphs)} 个段落，仅显示前50个）"

            # 图片提示
            image_hint = f"注意：此文档包含 {image_count} 张图片/图表。" if image_count > 0 else ""

            prompt = f"""你是一个专业的数据提取专家。请从以下 Word 文档的完整内容中提取结构化数据。

【用户需求】
{user_hint if user_hint else "请提取文档中的所有结构化数据，包括表格数据、键值对、列表项等。"}

【文档正文（段落）】
{paragraphs_text}

【文档表格】
{tables_text}

【文档图片信息】
{image_hint}

请按照以下 JSON 格式输出：
{{
    "type": "table_data",
    "headers": ["列1", "列2", ...],
    "rows": [["行1列1", "行1列2", ...], ["行2列1", "行2列2", ...], ...],
    "key_values": {{"键1": "值1", "键2": "值2", ...}},
    "list_items": ["项1", "项2", ...],
    "description": "文档内容描述"
}}

重点：
- 优先从表格中提取结构化数据
- 如果表格中有表头，headers 是表头，rows 是数据行
- 如果文档中有键值对（如 名称: 张三），提取到 key_values 中
- 如果文档中有列表项，提取到 list_items 中
- 图片内容无法直接提取，但请在 description 中说明图片的大致主题（如"包含流程图"、"包含数据图表"等）
"""

            messages = [
                {"role": "system", "content": "你是一个专业的数据提取助手。请严格按JSON格式输出。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=50000
            )

            content = self.llm.extract_message_content(response)

            # 解析 JSON
            result = self._parse_json_response(content)

            if result:
                logger.info(f"AI 表格提取成功: {len(result.get('rows', []))} 行数据, key_values={len(result.get('key_values', {}))}, list_items={len(result.get('list_items', []))}")
                return {
                    "success": True,
                    "type": "table_data",
                    "headers": result.get("headers", []),
                    "rows": result.get("rows", []),
                    "description": result.get("description", ""),
                    "key_values": result.get("key_values", {}),
                    "list_items": result.get("list_items", [])
                }
            else:
                # 如果 AI 返回格式不对，尝试直接解析表格
                return self._fallback_table_parse(tables)

        except Exception as e:
            logger.error(f"AI 表格提取失败: {str(e)}")
            return self._fallback_table_parse(tables)

    async def _extract_from_text_with_ai(
        self,
        paragraphs: List[str],
        full_text: str,
        image_count: int,
        image_descriptions: List[str],
        user_hint: str,
        image_analysis: str = ""
    ) -> Dict[str, Any]:
        """
        使用 AI 从 Word 纯文本中提取结构化数据

        Args:
            paragraphs: 段落列表
            full_text: 完整文本
            image_count: 图片数量
            image_descriptions: 图片描述列表
            user_hint: 用户提示
            image_analysis: 图片 AI 分析结果

        Returns:
            结构化数据
        """
        try:
            # 限制文本长度
            text_preview = full_text[:8000] if len(full_text) > 8000 else full_text

            # 图片提示
            image_hint = f"\n【文档图片】此文档包含 {image_count} 张图片/图表。" if image_count > 0 else ""
            if image_descriptions:
                image_hint += "\n" + "\n".join(image_descriptions)

            prompt = f"""你是一个专业的数据提取专家。请从以下 Word 文档的完整内容中提取结构化数据。

【用户需求】
{user_hint if user_hint else "请识别并提取文档中的关键信息，包括：表格数据、键值对、列表项等。"}

【文档正文】{image_hint}
{text_preview}

请按照以下 JSON 格式输出：
{{
    "type": "structured_text",
    "tables": [{{"headers": [...], "rows": [...]}}],
    "key_values": {{"键1": "值1", "键2": "值2", ...}},
    "list_items": ["项1", "项2", ...],
    "summary": "文档内容摘要"
}}

重点：
- 如果文档包含表格数据，提取到 tables 中
- 如果文档包含键值对（如 名称: 张三），提取到 key_values 中
- 如果文档包含列表项，提取到 list_items 中
- 如果文档包含图片，请根据上下文推断图片内容（如"流程图"、"数据折线图"等）并在 description 中说明
- 如果无法提取到结构化数据，至少提供一个详细的摘要
"""

            messages = [
                {"role": "system", "content": "你是一个专业的数据提取助手。请严格按JSON格式输出。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=50000
            )

            content = self.llm.extract_message_content(response)

            result = self._parse_json_response(content)

            if result:
                logger.info(f"AI 文本提取成功: type={result.get('type')}")
                return {
                    "success": True,
                    "type": result.get("type", "structured_text"),
                    "tables": result.get("tables", []),
                    "key_values": result.get("key_values", {}),
                    "list_items": result.get("list_items", []),
                    "summary": result.get("summary", ""),
                    "raw_text_preview": text_preview[:500]
                }
            else:
                return {
                    "success": True,
                    "type": "text",
                    "summary": text_preview[:500],
                    "raw_text_preview": text_preview[:500]
                }

        except Exception as e:
            logger.error(f"AI 文本提取失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _analyze_images_with_ai(
        self,
        images: List[Dict[str, str]],
        user_hint: str = ""
    ) -> str:
        """
        使用视觉模型分析 Word 文档中的图片

        Args:
            images: 图片列表，每项包含 base64 和 mime_type
            user_hint: 用户提示

        Returns:
            图片分析结果文本
        """
        try:
            # 调用 LLM 的视觉分析功能
            result = await self.llm.analyze_images(
                images=images,
                user_prompt=user_hint or "请详细描述图片内容，提取所有文字和数据信息。"
            )

            if result.get("success"):
                analysis = result.get("analysis", {})
                if isinstance(analysis, dict):
                    description = analysis.get("description", "")
                    text_content = analysis.get("text_content", "")
                    data_extracted = analysis.get("data_extracted", {})

                    result_text = f"【图片分析结果】\n{description}"
                    if text_content:
                        result_text += f"\n\n【图片中的文字】\n{text_content}"
                    if data_extracted:
                        result_text += f"\n\n【提取的数据】\n{json.dumps(data_extracted, ensure_ascii=False)}"
                    return result_text
                else:
                    return str(analysis)
            else:
                logger.warning(f"图片 AI 分析失败: {result.get('error')}")
                return ""

        except Exception as e:
            logger.error(f"图片 AI 分析异常: {str(e)}")
            return ""

    def _build_tables_description(self, tables: List[Dict]) -> str:
        """构建表格的文本描述"""
        result = []

        for idx, table in enumerate(tables):
            rows = table.get("rows", [])
            if not rows:
                continue

            result.append(f"\n--- 表格 {idx + 1} ---")

            for row_idx, row in enumerate(rows[:50]):  # 限制每表格最多50行
                if isinstance(row, list):
                    result.append(" | ".join(str(cell).strip() for cell in row))
                elif isinstance(row, dict):
                    result.append(str(row))

            if len(rows) > 50:
                result.append(f"...（共 {len(rows)} 行，仅显示前50行）")

        return "\n".join(result) if result else "（无表格内容）"

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """解析 JSON 响应，处理各种格式问题"""
        import re

        # 清理 markdown 标记
        cleaned = content.strip()
        cleaned = re.sub(r'^```json\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r'^```\s*', '', cleaned, flags=re.MULTILINE)
        cleaned = cleaned.strip()

        # 找到 JSON 开始位置
        json_start = -1
        for i, c in enumerate(cleaned):
            if c == '{':
                json_start = i
                break

        if json_start == -1:
            logger.warning("无法找到 JSON 开始位置")
            return None

        json_text = cleaned[json_start:]

        # 尝试直接解析
        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            pass

        # 尝试修复并解析
        try:
            # 找到闭合括号
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
                # 移除末尾逗号
                fixed = re.sub(r',\s*([}]])', r'\1', fixed)
                return json.loads(fixed)
        except Exception as e:
            logger.warning(f"JSON 修复失败: {e}")

        return None

    def _fallback_table_parse(self, tables: List[Dict]) -> Dict[str, Any]:
        """当 AI 解析失败时，直接解析表格"""
        if not tables:
            return {
                "success": True,
                "type": "empty",
                "data": {},
                "message": "无表格内容"
            }

        all_rows = []
        all_headers = None

        for table in tables:
            rows = table.get("rows", [])
            if not rows:
                continue

            # 查找真正的表头行（跳过标题行）
            header_row_idx = 0
            for idx, row in enumerate(rows[:5]):  # 只检查前5行
                if not isinstance(row, list):
                    continue
                # 如果某一行包含"表"字开头且单元格内容很长，这可能是标题行
                first_cell = str(row[0]) if row else ""
                if first_cell.startswith("表") and len(first_cell) > 15:
                    header_row_idx = idx + 1
                    continue
                # 如果某一行有超过3个空单元格，可能是无效行
                empty_count = sum(1 for cell in row if not str(cell).strip())
                if empty_count > 3:
                    header_row_idx = idx + 1
                    continue
                # 找到第一行看起来像表头的行（短单元格，大部分有内容）
                avg_len = sum(len(str(c)) for c in row) / len(row) if row else 0
                if avg_len < 20:  # 表头通常比数据行短
                    header_row_idx = idx
                    break

            if header_row_idx >= len(rows):
                continue

            # 使用找到的表头行
            if rows and isinstance(rows[header_row_idx], list):
                headers = rows[header_row_idx]
                if all_headers is None:
                    all_headers = headers

                # 数据行（从表头之后开始）
                for row in rows[header_row_idx + 1:]:
                    if isinstance(row, list) and len(row) == len(headers):
                        all_rows.append(row)

        if all_headers and all_rows:
            return {
                "success": True,
                "type": "table_data",
                "headers": all_headers,
                "rows": all_rows,
                "description": "直接从 Word 表格提取"
            }

        return {
            "success": True,
            "type": "raw",
            "tables": tables,
            "message": "表格数据（未AI处理）"
        }

    async def fill_template_with_ai(
        self,
        file_path: str,
        template_fields: List[Dict[str, Any]],
        user_hint: str = ""
    ) -> Dict[str, Any]:
        """
        使用 AI 解析 Word 文档并填写模板

        这是主要入口函数，前端调用此函数即可完成：
        1. AI 解析 Word 文档
        2. 根据模板字段提取数据
        3. 返回填写结果

        Args:
            file_path: Word 文件路径
            template_fields: 模板字段列表 [{"name": "字段名", "hint": "提示词"}, ...]
            user_hint: 用户提示

        Returns:
            填写结果
        """
        try:
            # 1. AI 解析文档
            parse_result = await self.parse_word_with_ai(file_path, user_hint)

            if not parse_result.get("success"):
                return {
                    "success": False,
                    "error": parse_result.get("error", "解析失败"),
                    "filled_data": {},
                    "source": "ai_parse_failed"
                }

            # 2. 根据字段类型提取数据
            filled_data = {}
            extract_details = []

            parse_type = parse_result.get("type", "")

            if parse_type == "table_data":
                # 表格数据：直接匹配列名
                headers = parse_result.get("headers", [])
                rows = parse_result.get("rows", [])

                for field in template_fields:
                    field_name = field.get("name", "")
                    values = self._extract_field_from_table(headers, rows, field_name)
                    filled_data[field_name] = values
                    extract_details.append({
                        "field": field_name,
                        "values": values,
                        "source": "ai_table_extraction",
                        "confidence": 0.9 if values else 0.0
                    })

            elif parse_type == "structured_text":
                # 结构化文本：尝试从 key_values 和 list_items 提取
                key_values = parse_result.get("key_values", {})
                list_items = parse_result.get("list_items", [])

                for field in template_fields:
                    field_name = field.get("name", "")
                    value = key_values.get(field_name, "")
                    if not value and list_items:
                        value = list_items[0] if list_items else ""
                    filled_data[field_name] = [value] if value else []
                    extract_details.append({
                        "field": field_name,
                        "values": [value] if value else [],
                        "source": "ai_text_extraction",
                        "confidence": 0.7 if value else 0.0
                    })

            else:
                # 其他类型：返回原始解析结果供后续处理
                for field in template_fields:
                    field_name = field.get("name", "")
                    filled_data[field_name] = []
                    extract_details.append({
                        "field": field_name,
                        "values": [],
                        "source": "no_ai_data",
                        "confidence": 0.0
                    })

            # 3. 返回结果
            max_rows = max(len(v) for v in filled_data.values()) if filled_data else 1

            return {
                "success": True,
                "filled_data": filled_data,
                "fill_details": extract_details,
                "ai_parse_result": {
                    "type": parse_type,
                    "description": parse_result.get("description", "")
                },
                "source_doc_count": 1,
                "max_rows": max_rows
            }

        except Exception as e:
            logger.error(f"AI 填表失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "filled_data": {},
                "fill_details": []
            }

    def _extract_field_from_table(
        self,
        headers: List[str],
        rows: List[List],
        field_name: str
    ) -> List[str]:
        """从表格中提取指定字段的值"""
        # 查找匹配的列
        target_col_idx = None
        for col_idx, header in enumerate(headers):
            if field_name.lower() in str(header).lower() or str(header).lower() in field_name.lower():
                target_col_idx = col_idx
                break

        if target_col_idx is None:
            return []

        # 提取该列所有值
        values = []
        for row in rows:
            if isinstance(row, list) and target_col_idx < len(row):
                val = str(row[target_col_idx]).strip()
                if val:
                    values.append(val)

        return values

    async def generate_charts(
        self,
        file_path: str,
        user_hint: str = ""
    ) -> Dict[str, Any]:
        """
        使用 AI 解析 Word 文档并生成可视化图表

        从 Word 文档中提取表格数据，然后生成统计图表

        Args:
            file_path: Word 文件路径
            user_hint: 用户提示词，指定要提取的内容类型

        Returns:
            Dict: 包含图表数据和统计信息的结果
        """
        try:
            # 1. 先用基础解析器提取原始内容
            parse_result = self.parser.parse(file_path)

            if not parse_result.success:
                return {
                    "success": False,
                    "error": parse_result.error,
                    "structured_data": None
                }

            # 2. 获取原始数据
            raw_data = parse_result.data
            paragraphs = raw_data.get("paragraphs", [])
            tables = raw_data.get("tables", [])
            content = raw_data.get("content", "")

            logger.info(f"Word 基础解析完成: {len(paragraphs)} 个段落, {len(tables)} 个表格")

            # 3. 优先处理表格数据
            if tables and len(tables) > 0:
                structured_data = await self._extract_tables_with_ai(
                    tables, paragraphs, 0, user_hint, parse_result.metadata
                )
            elif paragraphs and len(paragraphs) > 0:
                structured_data = await self._extract_from_text_with_ai(
                    paragraphs, content, 0, [], user_hint
                )
            else:
                return {
                    "success": False,
                    "error": "文档内容为空",
                    "structured_data": None
                }

            # 4. 检查是否有表格数据用于可视化
            if not structured_data.get("success"):
                return {
                    "success": False,
                    "error": structured_data.get("error", "解析失败"),
                    "structured_data": None
                }

            parse_type = structured_data.get("type", "")

            # 5. 提取可用于图表的数据
            chart_data = None

            if parse_type == "table_data":
                headers = structured_data.get("headers", [])
                rows = structured_data.get("rows", [])
                if headers and rows:
                    chart_data = {
                        "columns": headers,
                        "rows": rows
                    }
            elif parse_type == "structured_text":
                tables = structured_data.get("tables", [])
                if tables and len(tables) > 0:
                    first_table = tables[0]
                    headers = first_table.get("headers", [])
                    rows = first_table.get("rows", [])
                    if headers and rows:
                        chart_data = {
                            "columns": headers,
                            "rows": rows
                        }

            # 6. 生成可视化图表
            if chart_data:
                logger.info(f"开始生成图表，列数: {len(chart_data['columns'])}, 行数: {len(chart_data['rows'])}")
                vis_result = visualization_service.analyze_and_visualize(chart_data)

                if vis_result.get("success"):
                    return {
                        "success": True,
                        "charts": vis_result.get("charts", {}),
                        "statistics": vis_result.get("statistics", {}),
                        "distributions": vis_result.get("distributions", {}),
                        "structured_data": structured_data,
                        "row_count": vis_result.get("row_count", 0),
                        "column_count": vis_result.get("column_count", 0)
                    }
                else:
                    return {
                        "success": False,
                        "error": vis_result.get("error", "可视化生成失败"),
                        "structured_data": structured_data
                    }
            else:
                return {
                    "success": False,
                    "error": "文档中没有可用于图表的表格数据",
                    "structured_data": structured_data
                }

        except Exception as e:
            logger.error(f"Word 文档图表生成失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "structured_data": None
            }


# 全局单例
word_ai_service = WordAIService()
