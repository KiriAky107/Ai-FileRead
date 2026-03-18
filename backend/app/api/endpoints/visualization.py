"""
可视化 API 接口 - 生成统计图表
"""
from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any
import logging

from app.services.visualization_service import visualization_service
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/visualization", tags=["数据可视化"])


class StatisticsRequest(BaseModel):
    """统计图表生成请求模型"""
    excel_data: Dict[str, Any]
    analysis_type: str = "statistics"


@router.post("/statistics")
async def generate_statistics(request: StatisticsRequest):
    """
    生成统计信息和可视化图表

    Args:
        request: 包含 excel_data 和 analysis_type 的请求体

    Returns:
        dict: 包含统计信息和图表数据的结果
    """
    excel_data = request.excel_data
    analysis_type = request.analysis_type

    if not excel_data:
        raise HTTPException(status_code=400, detail="未提供 Excel 数据")

    try:
        result = visualization_service.analyze_and_visualize(
            excel_data,
            analysis_type
        )

        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error", "分析失败"))

        logger.info("统计图表生成成功")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"统计图表生成失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"图表生成失败: {str(e)}")


@router.get("/chart-types")
async def get_chart_types():
    """
    获取支持的图表类型

    Returns:
        dict: 支持的图表类型列表
    """
    return {
        "chart_types": [
            {
                "value": "histogram",
                "label": "直方图",
                "description": "显示数值型列的分布情况"
            },
            {
                "value": "bar_chart",
                "label": "条形图",
                "description": "显示分类列的频次分布"
            },
            {
                "value": "box_plot",
                "label": "箱线图",
                "description": "显示数值列的四分位数和异常值"
            },
            {
                "value": "correlation_heatmap",
                "label": "相关性热力图",
                "description": "显示数值列之间的相关性"
            }
        ]
    }
