"""
AI 分析 API 接口
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import tempfile
import os

from app.services.excel_ai_service import excel_ai_service
from app.services.markdown_ai_service import markdown_ai_service
from app.services.word_ai_service import word_ai_service

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
        dict: 支持的分析类型（包含 Excel 和 Markdown）
    """
    return {
        "excel_types": excel_ai_service.get_supported_analysis_types(),
        "markdown_types": markdown_ai_service.get_supported_analysis_types()
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


@router.post("/analyze/md")
async def analyze_markdown(
    file: UploadFile = File(...),
    analysis_type: str = Query("summary", description="分析类型: summary, outline, key_points, questions, tags, qa, statistics, section"),
    user_prompt: str = Query("", description="用户自定义提示词"),
    section_number: Optional[str] = Query(None, description="指定章节编号，如 '一' 或 '（一）'")
):
    """
    上传并使用 AI 分析 Markdown 文件

    Args:
        file: 上传的 Markdown 文件
        analysis_type: 分析类型
        user_prompt: 用户自定义提示词
        section_number: 指定分析的章节编号

    Returns:
        dict: 分析结果
    """
    # 检查文件类型
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['md', 'markdown']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .md 和 .markdown"
        )

    # 验证分析类型
    supported_types = markdown_ai_service.get_supported_analysis_types()
    if analysis_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的分析类型: {analysis_type}，支持的类型: {', '.join(supported_types)}"
        )

    try:
        # 读取文件内容
        content = await file.read()

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.md', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            logger.info(f"开始分析 Markdown 文件: {file.filename}, 分析类型: {analysis_type}, 章节: {section_number}")

            # 调用 AI 分析服务
            result = await markdown_ai_service.analyze_markdown(
                file_path=tmp_path,
                analysis_type=analysis_type,
                user_prompt=user_prompt,
                section_number=section_number
            )

            logger.info(f"Markdown 分析完成: {file.filename}, 成功: {result['success']}")

            if not result['success']:
                raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))

            return result

        finally:
            # 清理临时文件，确保在所有情况下都能清理
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"临时文件清理失败: {tmp_path}, error: {cleanup_error}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Markdown AI 分析过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/analyze/md/stream")
async def analyze_markdown_stream(
    file: UploadFile = File(...),
    analysis_type: str = Query("summary", description="分析类型"),
    user_prompt: str = Query("", description="用户自定义提示词"),
    section_number: Optional[str] = Query(None, description="指定章节编号")
):
    """
    流式分析 Markdown 文件 (SSE)

    Returns:
        StreamingResponse: SSE 流式响应
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['md', 'markdown']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .md 和 .markdown"
        )

    try:
        content = await file.read()

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.md', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            logger.info(f"开始流式分析 Markdown 文件: {file.filename}, 分析类型: {analysis_type}")

            async def stream_generator():
                async for chunk in markdown_ai_service.analyze_markdown_stream(
                    file_path=tmp_path,
                    analysis_type=analysis_type,
                    user_prompt=user_prompt,
                    section_number=section_number
                ):
                    yield chunk

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )

        finally:
            # 清理临时文件，确保在所有情况下都能清理
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"临时文件清理失败: {tmp_path}, error: {cleanup_error}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Markdown AI 流式分析出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"流式分析失败: {str(e)}")


@router.post("/analyze/md/outline")
async def get_markdown_outline(
    file: UploadFile = File(...)
):
    """
    获取 Markdown 文档的大纲结构（分章节信息）

    Args:
        file: 上传的 Markdown 文件

    Returns:
        dict: 文档大纲结构
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['md', 'markdown']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .md 和 .markdown"
        )

    try:
        content = await file.read()

        with tempfile.NamedTemporaryFile(mode='wb', suffix='.md', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            result = await markdown_ai_service.extract_outline(tmp_path)
            return result
        finally:
            # 清理临时文件，确保在所有情况下都能清理
            try:
                if tmp_path and os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"临时文件清理失败: {tmp_path}, error: {cleanup_error}")

    except Exception as e:
        logger.error(f"获取 Markdown 大纲失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取大纲失败: {str(e)}")


# ==================== Word 文档 AI 解析 ====================

@router.post("/analyze/word")
async def analyze_word(
    file: UploadFile = File(...),
    user_hint: str = Query("", description="用户提示词，如'请提取表格数据'")
):
    """
    使用 AI 解析 Word 文档，提取结构化数据

    适用于从非结构化的 Word 文档中提取表格数据、键值对等信息

    Args:
        file: 上传的 Word 文件
        user_hint: 用户提示词

    Returns:
        dict: 包含结构化数据的解析结果
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['docx']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .docx"
        )

    try:
        content = await file.read()

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            logger.info(f"开始 AI 解析 Word 文件: {file.filename}")

            result = await word_ai_service.parse_word_with_ai(
                file_path=tmp_path,
                user_hint=user_hint
            )

            logger.info(f"Word AI 解析完成: {file.filename}, success={result.get('success')}")

            return result

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Word AI 解析出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 解析失败: {str(e)}")


@router.post("/analyze/word/fill-template")
async def fill_template_with_word_ai(
    file: UploadFile = File(...),
    template_fields: str = Query("", description="模板字段，JSON字符串"),
    user_hint: str = Query("", description="用户提示词")
):
    """
    使用 AI 解析 Word 文档并填写模板

    前端调用此接口即可完成：AI解析 + 填表

    Args:
        file: 上传的 Word 文件
        template_fields: 模板字段 JSON 字符串
        user_hint: 用户提示词

    Returns:
        dict: 填写结果
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['docx']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .docx"
        )

    try:
        import json as json_module
        fields = json_module.loads(template_fields) if template_fields else []
    except json_module.JSONDecodeError:
        raise HTTPException(status_code=400, detail="template_fields 格式错误，应为 JSON 数组")

    try:
        content = await file.read()

        # 保存到临时文件
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.docx', delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            logger.info(f"开始 AI 填表（Word）: {file.filename}, 字段数: {len(fields)}")

            result = await word_ai_service.fill_template_with_ai(
                file_path=tmp_path,
                template_fields=fields,
                user_hint=user_hint
            )

            logger.info(f"Word AI 填表完成: {file.filename}, success={result.get('success')}")

            return result

        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Word AI 填表出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI 填表失败: {str(e)}")
