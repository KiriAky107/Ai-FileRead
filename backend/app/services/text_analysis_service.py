"""
文本分析服务 - 从 AI 分析结果中提取结构化数据用于可视化
"""
import logging
from typing import Dict, Any, List, Optional
import re
import json

from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class TextAnalysisService:
    """文本分析服务类"""

    def __init__(self):
        self.llm_service = llm_service

    async def extract_structured_data(
        self,
        analysis_text: str,
        original_filename: str = "",
        file_type: str = "text"
    ) -> Dict[str, Any]:
        """
        从 AI 分析结果文本中提取结构化数据

        Args:
            analysis_text: AI 分析结果文本
            original_filename: 原始文件名
            file_type: 文件类型

        Returns:
            Dict[str, Any]: 提取的结构化数据
        """
        # 限制分析的文本长度，避免 token 超限
        max_text_length = 8000
        truncated_text = analysis_text[:max_text_length]

        system_prompt = """你是一个专业的数据提取助手。你的任务是从AI分析结果中提取结构化数据，用于生成图表。

请按照以下要求提取数据：

1. 数值型数据：
   - 提取所有的数值、统计信息、百分比等
   - 为每个数值创建一个条目，包含：名称、值、单位（如果有）
   - 格式示例：{"name": "销售额", "value": 123456.78, "unit": "元"}

2. 分类数据：
   - 提取所有的类别、状态、枚举值等
   - 为每个类别创建一个条目，包含：名称、值、数量（如果有）
   - 格式示例：{"name": "产品类别", "value": "电子产品", "count": 25}

3. 时间序列数据：
   - 提取所有的时间相关数据（年月、季度、日期等）
   - 格式示例：{"name": "2025年1月", "value": 12345}

4. 对比数据：
   - 提取所有的对比、排名、趋势等数据
   - 格式示例：{"name": "同比增长", "value": 15.3, "unit": "%"}

5. 表格数据：
   - 如果分析结果中包含表格或列表形式的数据，提取出来
   - 格式：{"columns": ["列1", "列2"], "rows": [{"列1": "值1", "列2": "值2"}]}

重要规则：
- 只提取明确提到的数据和数值
- 如果某种类型的数据不存在，返回空数组 []
- 确保所有数值都是有效的数字类型
- 保持数据的原始精度
- 返回的 JSON 必须完整且格式正确
- 表格数据最多提取 20 行

请以 JSON 格式返回，不要添加任何 Markdown 标记或解释文字，只返回纯 JSON：
{
  "success": true,
  "data": {
    "numeric_data": [
      {"name": string, "value": number, "unit": string|null}
    ],
    "categorical_data": [
      {"name": string, "value": string, "count": number|null}
    ],
    "time_series_data": [
      {"name": string, "value": number}
    ],
    "comparison_data": [
      {"name": string, "value": number, "unit": string|null}
    ],
    "table_data": {
      "columns": string[],
      "rows": object[]
    } | null
  },
  "metadata": {
    "total_items": number,
    "data_types": string[]
  }
}"""

        user_message = f"""请从以下 AI 分析结果中提取结构化数据：

原始文件名：{original_filename}
文件类型：{file_type}

AI 分析结果：
{truncated_text}

请按照系统提示的要求提取数据并返回纯 JSON 格式。"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            logger.info(f"开始提取结构化数据，文本长度: {len(truncated_text)}")

            response = await self.llm_service.chat(
                messages=messages,
                temperature=0.1,
                max_tokens=4000
            )

            content = self.llm_service.extract_message_content(response)
            logger.info(f"LLM 返回内容长度: {len(content)}")

            # 使用简单的方法提取 JSON
            result = self._extract_json_simple(content)

            if not result:
                logger.error("无法从 LLM 响应中提取有效的 JSON")
                return {
                    "success": False,
                    "error": "AI 返回的数据格式不正确或被截断",
                    "raw_content": content[:500]
                }

            logger.info(f"成功提取结构化数据")
            return result

        except Exception as e:
            logger.error(f"提取结构化数据失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_json_simple(self, content: str) -> Optional[Dict[str, Any]]:
        """
        简化的 JSON 提取方法

        Args:
            content: LLM 返回的内容

        Returns:
            Optional[Dict[str, Any]]: 解析后的 JSON，失败返回 None
        """
        try:
            # 方法 1: 查找 ```json 代码块
            code_block_match = re.search(r'```json\n{[\s\S]*?}[\s\S]*?}\n```', content, re.DOTALL)
            if code_block_match:
                json_str = code_block_match.group(1)
                logger.info("从代码块中提取 JSON")
                return json.loads(json_str)

            # 方法 2: 查找第一个完整的 { } 对象
            brace_count = 0
            json_start = -1

            for i in range(len(content)):
                if content[i] == '{':
                    if brace_count == 0:
                        json_start = i
                    brace_count += 1
                elif content[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        # 找到了完整的 JSON 对象
                        json_end = i + 1
                        json_str = content[json_start:json_end]
                        logger.info(f"从大括号中提取 JSON")
                        return json.loads(json_str)

            # 方法 3: 尝试直接解析
            logger.info("尝试直接解析整个内容")
            return json.loads(content)

        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析失败: {str(e)}")
            logger.error(f"原始内容（前 500 字符）: {content[:500]}...")
            return None
        except Exception as e:
            logger.error(f"提取 JSON 失败: {str(e)}")
            return None

    def detect_data_types(self, data: Dict[str, Any]) -> List[str]:
        """检测数据中包含的类型"""
        types = []
        d = data.get("data", {})

        if d.get("numeric_data") and len(d["numeric_data"]) > 0:
            types.append("numeric")
        if d.get("categorical_data") and len(d["categorical_data"]) > 0:
            types.append("categorical")
        if d.get("time_series_data") and len(d["time_series_data"]) > 0:
            types.append("time_series")
        if d.get("comparison_data") and len(d["comparison_data"]) > 0:
            types.append("comparison")
        if d.get("table_data") and d["table_data"]:
            types.append("table")

        return types


# 全局单例
text_analysis_service = TextAnalysisService()
