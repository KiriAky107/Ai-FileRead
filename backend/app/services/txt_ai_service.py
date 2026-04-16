"""
TXT 文档 AI 分析服务

使用 LLM 对 TXT 文本文件进行深度分析，提取结构化数据并生成可视化图表
"""
import logging
import re
from typing import Any, Dict, List, Optional

from app.services.llm_service import llm_service
from app.services.visualization_service import visualization_service
from app.core.document_parser.txt_parser import TxtParser

logger = logging.getLogger(__name__)


class TxtAIService:
    """TXT 文档 AI 分析服务"""

    def __init__(self):
        self.parser = TxtParser()

    async def analyze_txt_with_ai(
        self,
        content: str,
        filename: str = "",
        user_hint: str = "",
        analysis_type: str = "structured"
    ) -> Dict[str, Any]:
        """
        使用 AI 解析 TXT 文本文件

        Args:
            content: 文本内容
            filename: 文件名（可选）
            user_hint: 用户提示词
            analysis_type: 分析类型 - "structured"（默认，提取结构化数据）或 "charts"（生成图表）

        Returns:
            Dict: 包含结构化数据的分析结果
        """
        try:
            if not content or not content.strip():
                return {
                    "success": False,
                    "error": "文档内容为空"
                }

            # 根据分析类型选择处理方式
            if analysis_type == "charts":
                return await self.generate_charts(content, filename, user_hint)

            # 默认：提取结构化数据
            return await self._extract_structured_data(content, filename, user_hint)

        except Exception as e:
            logger.error(f"TXT AI 分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _extract_structured_data(
        self,
        content: str,
        filename: str = "",
        user_hint: str = ""
    ) -> Dict[str, Any]:
        """
        从文本中提取结构化数据

        Args:
            content: 文本内容
            filename: 文件名
            user_hint: 用户提示词

        Returns:
            结构化数据
        """
        try:
            # 截断内容避免超出 token 限制
            max_content_len = 8000
            text_preview = content[:max_content_len] if len(content) > max_content_len else content

            prompt = f"""你是一个专业的数据提取专家。请从以下文本中提取结构化数据。

【用户需求】
{user_hint if user_hint else "请提取文档中的所有结构化数据，包括表格数据、键值对、列表项等。"}

【文档内容】（{"前" + str(max_content_len) + "字符，仅显示部分" if len(content) > max_content_len else "全文"}）
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
- 如果文档包含表格数据（制表符、空格对齐等），提取到 tables 中
- 如果文档包含键值对（如 名称: 张三），提取到 key_values 中
- 如果文档包含列表项，提取到 list_items 中
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

            content_text = self.llm.extract_message_content(response)
            result = self._parse_json_response(content_text)

            if result:
                logger.info(f"TXT 结构化数据提取成功: type={result.get('type')}")
                return {
                    "success": True,
                    "type": result.get("type", "structured_text"),
                    "tables": result.get("tables", []),
                    "key_values": result.get("key_values", {}),
                    "list_items": result.get("list_items", []),
                    "summary": result.get("summary", "")
                }
            else:
                return {
                    "success": True,
                    "type": "text",
                    "summary": text_preview[:500],
                    "raw_text_preview": text_preview[:500]
                }

        except Exception as e:
            logger.error(f"TXT 结构化数据提取失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def generate_charts(
        self,
        content: str,
        filename: str = "",
        user_hint: str = ""
    ) -> Dict[str, Any]:
        """
        从文本中提取数据并生成可视化图表

        Args:
            content: 文本内容
            filename: 文件名
            user_hint: 用户提示词

        Returns:
            包含图表数据和统计信息的结果
        """
        try:
            # 截断内容避免超出 token 限制
            max_content_len = 8000
            text_preview = content[:max_content_len] if len(content) > max_content_len else content

            # 使用 LLM 提取可用于图表的数据
            prompt = f"""你是一个专业的数据可视化助手。请从以下文本中提取可用于可视化的数据。

文档标题：{filename}

文档内容：
{text_preview}

请完成以下任务：
1. 识别文本中的表格数据（制表符分隔、空格对齐的表格等）
2. 识别文本中的关键统计数据（百分比、数量、趋势等）
3. 识别可用于比较的分类数据

请用 JSON 格式返回以下结构的数据（如果没有表格数据，返回空结构）：
{{
  "tables": [
    {{
      "description": "表格的描述",
      "columns": ["列名1", "列名2", ...],
      "rows": [
        ["值1", "值2", ...],
        ["值1", "值2", ...]
      ]
    }}
  ],
  "key_statistics": [
    {{
      "name": "指标名称",
      "value": "数值",
      "trend": "增长/下降/持平",
      "description": "指标说明"
    }}
  ],
  "chart_suggestions": [
    {{
      "chart_type": "bar/line/pie",
      "title": "图表标题",
      "data_source": "数据来源说明"
    }}
  ]
}}

如果没有表格数据，返回空结构：{{"tables": [], "key_statistics": [], "chart_suggestions": []}}
请确保返回的是合法的 JSON 格式。"""

            messages = [
                {"role": "system", "content": "你是一个专业的数据可视化助手，擅长从文本中提取数据并生成图表。"},
                {"role": "user", "content": prompt}
            ]

            response = await self.llm.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=50000
            )

            content_text = self.llm.extract_message_content(response)
            chart_data = self._parse_json_response(content_text)

            if not chart_data:
                return {
                    "success": False,
                    "error": "无法从文本中提取有效的数据结构"
                }

            # 检查是否有表格数据
            tables = chart_data.get("tables", [])
            key_statistics = chart_data.get("key_statistics", [])

            if not tables:
                return {
                    "success": False,
                    "error": "文档中没有可用于图表的表格数据",
                    "key_statistics": key_statistics,
                    "chart_suggestions": chart_data.get("chart_suggestions", [])
                }

            # 使用第一个表格生成图表
            first_table = tables[0]
            columns = first_table.get("columns", [])
            rows = first_table.get("rows", [])

            if not columns or not rows:
                return {
                    "success": False,
                    "error": "表格数据为空"
                }

            # 转换为 visualization_service 需要的格式
            viz_data = {
                "columns": columns,
                "rows": rows
            }

            # 生成可视化图表
            logger.info(f"开始生成图表，列数: {len(columns)}, 行数: {len(rows)}")
            vis_result = visualization_service.analyze_and_visualize(viz_data)

            if vis_result.get("success"):
                return {
                    "success": True,
                    "charts": vis_result.get("charts", {}),
                    "statistics": vis_result.get("statistics", {}),
                    "distributions": vis_result.get("distributions", {}),
                    "row_count": vis_result.get("row_count", 0),
                    "column_count": vis_result.get("column_count", 0),
                    "key_statistics": key_statistics,
                    "chart_suggestions": chart_data.get("chart_suggestions", []),
                    "table_description": first_table.get("description", "")
                }
            else:
                return {
                    "success": False,
                    "error": vis_result.get("error", "可视化生成失败"),
                    "key_statistics": key_statistics
                }

        except Exception as e:
            logger.error(f"TXT 图表生成失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _parse_json_response(self, content: str) -> Optional[Dict]:
        """解析 JSON 响应，处理各种格式问题"""
        if not content:
            return None

        import json

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


# 全局单例
txt_ai_service = TxtAIService()
