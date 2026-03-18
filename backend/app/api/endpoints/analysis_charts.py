"""
分析结果图表 API - 根据文本分析结果生成图表
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging

from app.services.text_analysis_service import text_analysis_service
from app.services.chart_generator_service import chart_generator_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["分析结果图表"])


class AnalysisChartRequest(BaseModel):
    """分析图表生成请求模型"""
    analysis_text: str
    original_filename: Optional[str] = ""
    file_type: Optional[str] = "text"


@router.post("/extract-and-chart")
async def extract_and_generate_charts(request: AnalysisChartRequest):
    """
    从 AI 分析结果中提取数据并生成图表

    Args:
        request: 包含分析文本的请求

    Returns:
        dict: 包含图表数据的结果
    """
    if not request.analysis_text or not request.analysis_text.strip():
        raise HTTPException(status_code=400, detail="分析文本不能为空")

    try:
        logger.info("开始从分析结果中提取结构化数据...")

        # 1. 使用 LLM 提取结构化数据
        extract_result = await text_analysis_service.extract_structured_data(
            analysis_text=request.analysis_text,
            original_filename=request.original_filename or "unknown",
            file_type=request.file_type or "text"
        )

        if not extract_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"提取结构化数据失败: {extract_result.get('error', '未知错误')}"
            )

        logger.info("结构化数据提取成功，开始生成图表...")

        # 2. 根据提取的数据生成图表
        chart_result = chart_generator_service.generate_charts_from_analysis(extract_result)

        if not chart_result.get("success"):
            raise HTTPException(
                status_code=500,
                detail=f"生成图表失败: {chart_result.get('error', '未知错误')}"
            )

        logger.info("图表生成成功")

        return chart_result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"分析结果图表生成失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"图表生成失败: {str(e)}"
        )


@router.post("/analyze-text")
async def analyze_text_only(request: AnalysisChartRequest):
    """
    仅提取结构化数据（不生成图表），用于调试

    Args:
        request: 包含分析文本的请求

    Returns:
        dict: 提取的结构化数据
    """
    if not request.analysis_text or not request.analysis_text.strip():
        raise HTTPException(status_code=400, detail="分析文本不能为空")

    try:
        result = await text_analysis_service.extract_structured_data(
            analysis_text=request.analysis_text,
            original_filename=request.original_filename or "unknown",
            file_type=request.file_type or "text"
        )
        return result
    except Exception as e:
        logger.error(f"文本分析失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文本分析失败: {str(e)}"
        )
