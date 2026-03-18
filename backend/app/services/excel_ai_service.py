"""
Excel AI 分析服务 - 集成 Excel 解析和 LLM 分析
"""
import logging
from typing import Dict, Any, Optional, List

from app.core.document_parser import XlsxParser
from app.services.file_service import file_service
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class ExcelAIService:
    """Excel AI 分析服务"""

    def __init__(self):
        self.parser = XlsxParser()
        self.file_service = file_service
        self.llm_service = llm_service

    async def analyze_excel_file(
        self,
        file_content: bytes,
        filename: str,
        user_prompt: str = "",
        analysis_type: str = "general",
        parse_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        分析 Excel 文件

        Args:
            file_content: 文件内容字节
            filename: 文件名
            user_prompt: 用户自定义提示词
            analysis_type: 分析类型
            parse_options: 解析选项

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 1. 保存文件
        try:
            saved_path = self.file_service.save_uploaded_file(
                file_content,
                filename,
                subfolder="excel"
            )
            logger.info(f"文件已保存: {saved_path}")
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            return {
                "success": False,
                "error": f"文件保存失败: {str(e)}",
                "analysis": None
            }

        # 2. 解析 Excel 文件
        try:
            parse_options = parse_options or {}
            parse_result = self.parser.parse(saved_path, **parse_options)

            if not parse_result.success:
                return {
                    "success": False,
                    "error": parse_result.error,
                    "analysis": None
                }

            excel_data = parse_result.data
            logger.info(f"Excel 解析成功: {parse_result.metadata}")

        except Exception as e:
            logger.error(f"Excel 解析失败: {str(e)}")
            return {
                "success": False,
                "error": f"Excel 解析失败: {str(e)}",
                "analysis": None
            }

        # 3. 调用 LLM 进行分析
        try:
            # 如果有自定义提示词，使用模板分析
            if user_prompt and user_prompt.strip():
                llm_result = await self.llm_service.analyze_with_template(
                    excel_data,
                    user_prompt
                )
            else:
                # 否则使用标准分析
                llm_result = await self.llm_service.analyze_excel_data(
                    excel_data,
                    user_prompt,
                    analysis_type
                )

            logger.info(f"AI 分析完成: {llm_result['success']}")

            # 4. 组合结果
            return {
                "success": True,
                "excel": {
                    "data": excel_data,
                    "metadata": parse_result.metadata,
                    "saved_path": saved_path
                },
                "analysis": llm_result
            }

        except Exception as e:
            logger.error(f"AI 分析失败: {str(e)}")
            return {
                "success": False,
                "error": f"AI 分析失败: {str(e)}",
                "excel": {
                    "data": excel_data,
                    "metadata": parse_result.metadata
                },
                "analysis": None
            }

    async def batch_analyze_sheets(
        self,
        file_content: bytes,
        filename: str,
        user_prompt: str = "",
        analysis_type: str = "general"
    ) -> Dict[str, Any]:
        """
        批量分析 Excel 文件的所有工作表

        Args:
            file_content: 文件内容字节
            filename: 文件名
            user_prompt: 用户自定义提示词
            analysis_type: 分析类型

        Returns:
            Dict[str, Any]: 分析结果
        """
        # 1. 保存文件
        try:
            saved_path = self.file_service.save_uploaded_file(
                file_content,
                filename,
                subfolder="excel"
            )
            logger.info(f"文件已保存: {saved_path}")
        except Exception as e:
            logger.error(f"文件保存失败: {str(e)}")
            return {
                "success": False,
                "error": f"文件保存失败: {str(e)}",
                "analysis": None
            }

        # 2. 解析所有工作表
        try:
            parse_result = self.parser.parse_all_sheets(saved_path)

            if not parse_result.success:
                return {
                    "success": False,
                    "error": parse_result.error,
                    "analysis": None
                }

            sheets_data = parse_result.data.get("sheets", {})
            logger.info(f"Excel 解析成功，共 {len(sheets_data)} 个工作表")

        except Exception as e:
            logger.error(f"Excel 解析失败: {str(e)}")
            return {
                "success": False,
                "error": f"Excel 解析失败: {str(e)}",
                "analysis": None
            }

        # 3. 批量分析每个工作表
        sheet_analyses = {}
        errors = {}

        for sheet_name, sheet_data in sheets_data.items():
            try:
                # 调用 LLM 分析
                if user_prompt and user_prompt.strip():
                    llm_result = await self.llm_service.analyze_with_template(
                        sheet_data,
                        user_prompt
                    )
                else:
                    llm_result = await self.llm_service.analyze_excel_data(
                        sheet_data,
                        user_prompt,
                        analysis_type
                    )

                sheet_analyses[sheet_name] = llm_result

                if not llm_result["success"]:
                    errors[sheet_name] = llm_result.get("error", "未知错误")

                logger.info(f"工作表 '{sheet_name}' 分析完成")

            except Exception as e:
                logger.error(f"工作表 '{sheet_name}' 分析失败: {str(e)}")
                errors[sheet_name] = str(e)

        # 4. 组合结果
        return {
            "success": len(errors) == 0,
            "excel": {
                "sheets": sheets_data,
                "metadata": parse_result.metadata,
                "saved_path": saved_path
            },
            "analysis": {
                "sheets": sheet_analyses,
                "total_sheets": len(sheets_data),
                "successful": len(sheet_analyses) - len(errors),
                "errors": errors
            }
        }

    def get_supported_analysis_types(self) -> List[str]:
        """获取支持的分析类型"""
        return [
            {
                "value": "general",
                "label": "综合分析",
                "description": "提供数据概览、关键发现、质量评估和建议"
            },
            {
                "value": "summary",
                "label": "数据摘要",
                "description": "快速了解数据的结构、范围和主要内容"
            },
            {
                "value": "statistics",
                "label": "统计分析",
                "description": "数值型列的统计信息和分类列的分布"
            },
            {
                "value": "insights",
                "label": "深度洞察",
                "description": "深入挖掘数据，提供异常值和业务建议"
            }
        ]


# 全局单例
excel_ai_service = ExcelAIService()
