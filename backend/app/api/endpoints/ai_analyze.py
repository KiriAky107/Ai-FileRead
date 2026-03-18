"""
AI 分析 API 接口
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body
from typing import Optional
import logging

from app.services.excel_ai_service import excel_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI 分析"])


@router.post("/analyze/excel")
async def analyze_excel(
    file: UploadFile = File(...),
    user_prompt: str = Query("", description="用户自定义提示词"),
    analysis_type: str = Query("general", description="分析类型: general, summary, statistics, insights"),
    parse_all_sheets: bool = Query(False, description="是否分析所有工作表")
):
    """
    上传并使用 AI 分析 Excel 文件

    Args:
        file: 上传的 Excel 文件
        user_prompt: 用户自定义提示词
        analysis_type: 分析类型
        parse_all_sheets: 是否分析所有工作表

    Returns:
        dict: 分析结果，包含 Excel 数据和 AI 分析结果
    """
    # 检查文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['xlsx', 'xls']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .xlsx 和 .xls"
        )

    # 验证分析类型
    supported_types = ['general', 'summary', 'statistics', 'insights']
    if analysis_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的分析类型: {analysis_type}，支持的类型: {', '.join(supported_types)}"
        )

    try:
        # 读取文件内容
        content = await file.read()

        logger.info(f"开始分析文件: {file.filename}, 分析类型: {analysis_type}")

        # 调用 AI 分析服务
        if parse_all_sheets:
            result = await excel_ai_service.batch_analyze_sheets(
                content,
                file.filename,
                user_prompt=user_prompt,
                analysis_type=analysis_type
            )
        else:
            # 解析选项
            parse_options = {"header_row": 0}

            result = await excel_ai_service.analyze_excel_file(
                content,
                file.filename,
                user_prompt=user_prompt,
                analysis_type=analysis_type,
                parse_options=parse_options
            )

        logger.info(f"文件分析完成: {file.filename}, 成功: {result['success']}")

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI 分析过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.get("/analysis/types")
async def get_analysis_types():
    """
    获取支持的分析类型列表

    Returns:
        list: 支持的分析类型
    """
    return {
        "types": excel_ai_service.get_supported_analysis_types()
    }


@router.post("/analyze/text")
async def analyze_text(
    excel_data: dict = Body(..., description="Excel 解析后的数据"),
    user_prompt: str = Body("", description="用户提示词"),
    analysis_type: str = Body("general", description="分析类型")
):
    """
    对已解析的 Excel 数据进行 AI 分析

    Args:
        excel_data: Excel 数据
        user_prompt: 用户提示词
        analysis_type: 分析类型

    Returns:
        dict: 分析结果
    """
    try:
        logger.info(f"开始文本分析, 分析类型: {analysis_type}")

        # 调用 LLM 服务
        from app.services.llm_service import llm_service

        if user_prompt and user_prompt.strip():
            result = await llm_service.analyze_with_template(
                excel_data,
                user_prompt
            )
        else:
            result = await llm_service.analyze_excel_data(
                excel_data,
                user_prompt,
                analysis_type
            )

        logger.info(f"文本分析完成, 成功: {result['success']}")

        return result

    except Exception as e:
        logger.error(f"文本分析失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
