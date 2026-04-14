"""
LLM 服务模块 - 封装大模型 API 调用
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    """大语言模型服务类"""

    def __init__(self):
        self.api_key = settings.LLM_API_KEY
        self.base_url = settings.LLM_BASE_URL
        self.model_name = settings.LLM_MODEL_NAME

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用聊天 API

        Args:
            messages: 消息列表，格式为 [{"role": "user", "content": "..."}]
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成 token 数
            **kwargs: 其他参数

        Returns:
            Dict[str, Any]: API 响应结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # 添加其他参数
        payload.update(kwargs)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"LLM API 请求失败: {e.response.status_code} - {error_detail}")
            # 尝试解析错误信息
            try:
                import json
                err_json = json.loads(error_detail)
                err_code = err_json.get("error", {}).get("code", "unknown")
                err_msg = err_json.get("error", {}).get("message", "unknown")
                logger.error(f"API 错误码: {err_code}, 错误信息: {err_msg}")
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"LLM API 调用异常: {str(e)}")
            raise

    def extract_message_content(self, response: Dict[str, Any]) -> str:
        """
        从 API 响应中提取消息内容

        Args:
            response: API 响应

        Returns:
            str: 消息内容
        """
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            logger.error(f"解析 API 响应失败: {str(e)}")
            raise

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        流式调用聊天 API

        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大 token 数
            **kwargs: 其他参数

        Yields:
            Dict[str, Any]: 包含 delta 内容的块
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]  # Remove "data: " prefix
                            if data == "[DONE]":
                                break
                            try:
                                import json as json_module
                                chunk = json_module.loads(data)
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield {"content": delta}
                            except json_module.JSONDecodeError:
                                continue

        except httpx.HTTPStatusError as e:
            logger.error(f"LLM 流式 API 请求失败: {e.response.status_code}")
            raise
        except Exception as e:
            logger.error(f"LLM 流式 API 调用异常: {str(e)}")
            raise

    async def analyze_excel_data(
        self,
        excel_data: Dict[str, Any],
        user_prompt: str,
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        分析 Excel 数据

        Args:
            excel_data: Excel 解析后的数据
            user_prompt: 用户提示词
            analysis_type: 分析类型 (general, summary, statistics, insights)

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 构建 Prompt
        system_prompt = self._get_system_prompt(analysis_type)
        user_message = self._format_user_message(excel_data, user_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat(
                messages=messages,
                temperature=0.3,  # 较低的温度以获得更稳定的输出
                max_tokens=2000
            )

            content = self.extract_message_content(response)

            return {
                "success": True,
                "analysis": content,
                "model": self.model_name,
                "analysis_type": analysis_type
            }

        except Exception as e:
            logger.error(f"Excel 数据分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }

    def _get_system_prompt(self, analysis_type: str) -> str:
        """获取系统提示词"""
        prompts = {
            "general": """你是一个专业的数据分析师。请分析用户提供的 Excel 数据，提供有价值的见解和建议。

请按照以下格式输出：
1. 数据概览
2. 关键发现
3. 数据质量评估
4. 建议

输出语言：中文""",
            "summary": """你是一个专业的数据分析师。请对用户提供的 Excel 数据进行简洁的总结。

输出格式：
- 数据行数和列数
- 主要列的说明
- 数据范围概述

输出语言：中文""",
            "statistics": """你是一个专业的数据分析师。请对用户提供的 Excel 数据进行统计分析。

请分析：
- 数值型列的统计信息（平均值、中位数、最大值、最小值）
- 分类列的分布情况
- 数据相关性

输出语言：中文，使用表格或结构化格式展示""",
            "insights": """你是一个专业的数据分析师。请深入挖掘用户提供的 Excel 数据，提供有价值的洞察。

请分析：
1. 数据中的异常值或特殊模式
2. 数据之间的潜在关联
3. 基于数据的业务建议
4. 数据趋势分析（如适用）

输出语言：中文，提供详细且可操作的建议"""
        }

        return prompts.get(analysis_type, prompts["general"])

    def _format_user_message(self, excel_data: Dict[str, Any], user_prompt: str) -> str:
        """格式化用户消息"""
        columns = excel_data.get("columns", [])
        rows = excel_data.get("rows", [])
        row_count = excel_data.get("row_count", 0)
        column_count = excel_data.get("column_count", 0)

        # 构建数据描述
        data_info = f"""
Excel 数据概览:
- 行数: {row_count}
- 列数: {column_count}
- 列名: {', '.join(columns)}

数据样例（前 5 行）:
"""

        # 添加数据样例
        for i, row in enumerate(rows[:5], 1):
            row_str = " | ".join([f"{col}: {row.get(col, '')}" for col in columns])
            data_info += f"第 {i} 行: {row_str}\n"

        if row_count > 5:
            data_info += f"\n(还有 {row_count - 5} 行数据...)\n"

        # 添加用户自定义提示
        if user_prompt and user_prompt.strip():
            data_info += f"\n用户需求:\n{user_prompt}"
        else:
            data_info += "\n用户需求: 请对上述数据进行分析"

        return data_info

    async def analyze_with_template(
        self,
        excel_data: Dict[str, Any],
        template_prompt: str
    ) -> Dict[str, Any]:
        """
        使用自定义模板分析 Excel 数据

        Args:
            excel_data: Excel 解析后的数据
            template_prompt: 自定义提示词模板

        Returns:
            Dict[str, Any]: 分析结果
        """
        system_prompt = """你是一个专业的数据分析师。请根据用户提供的自定义提示词分析 Excel 数据。

请严格按照用户的要求进行分析，输出清晰、有条理的结果。

输出语言：中文"""

        user_message = self._format_user_message(excel_data, template_prompt)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]

        try:
            response = await self.chat(
                messages=messages,
                temperature=0.5,
                max_tokens=3000
            )

            content = self.extract_message_content(response)

            return {
                "success": True,
                "analysis": content,
                "model": self.model_name,
                "is_template": True
            }

        except Exception as e:
            logger.error(f"自定义模板分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }

    async def chat_with_images(
        self,
        text: str,
        images: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        调用视觉模型 API（支持图片输入）

        Args:
            text: 文本内容
            images: 图片列表，每项包含 base64 编码和 mime_type
                   格式: [{"base64": "...", "mime_type": "image/png"}, ...]
            temperature: 温度参数
            max_tokens: 最大 token 数

        Returns:
            Dict[str, Any]: API 响应结果
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # 构建图片内容
        image_contents = []
        for img in images:
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{img['mime_type']};base64,{img['base64']}"
                }
            })

        # 构建消息
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    },
                    *image_contents
                ]
            }
        ]

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            logger.error(f"视觉模型 API 请求失败: {e.response.status_code} - {error_detail}")
            # 尝试解析错误信息
            try:
                import json
                err_json = json.loads(error_detail)
                err_code = err_json.get("error", {}).get("code", "unknown")
                err_msg = err_json.get("error", {}).get("message", "unknown")
                logger.error(f"API 错误码: {err_code}, 错误信息: {err_msg}")
                logger.error(f"请求模型: {self.model_name}, base_url: {self.base_url}")
            except:
                pass
            raise
        except Exception as e:
            logger.error(f"视觉模型 API 调用异常: {str(e)}")
            raise

    async def analyze_images(
        self,
        images: List[Dict[str, str]],
        user_prompt: str = ""
    ) -> Dict[str, Any]:
        """
        分析图片内容（使用视觉模型）

        Args:
            images: 图片列表，每项包含 base64 编码和 mime_type
            user_prompt: 用户提示词

        Returns:
            Dict[str, Any]: 分析结果
        """
        prompt = f"""你是一个专业的视觉分析专家。请分析以下图片内容。

{user_prompt if user_prompt else "请详细描述图片中的内容，包括文字、数据、图表、流程等所有可见信息。"}

请按照以下 JSON 格式输出：
{{
    "description": "图片内容的详细描述",
    "text_content": "图片中的文字内容（如有）",
    "data_extracted": {{"键": "值"}}  // 如果图片中有表格或数据
}}

如果图片不包含有用信息，请返回空的描述。"""

        try:
            response = await self.chat_with_images(
                text=prompt,
                images=images,
                temperature=0.1,
                max_tokens=4000
            )

            content = self.extract_message_content(response)

            # 解析 JSON
            import json
            try:
                result = json.loads(content)
                return {
                    "success": True,
                    "analysis": result,
                    "model": self.model_name
                }
            except json.JSONDecodeError:
                return {
                    "success": True,
                    "analysis": {"description": content},
                    "model": self.model_name
                }

        except Exception as e:
            logger.error(f"图片分析失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "analysis": None
            }


# 全局单例
llm_service = LLMService()
