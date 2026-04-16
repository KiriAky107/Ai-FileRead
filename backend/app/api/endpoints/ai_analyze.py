"""
AI 分析 API 接口
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Body, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import tempfile
import os

from app.services.excel_ai_service import excel_ai_service
from app.services.markdown_ai_service import markdown_ai_service
from app.services.template_fill_service import template_fill_service
from app.services.word_ai_service import word_ai_service
from app.services.txt_ai_service import txt_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI 分析"])


@router.post("/analyze/excel")
async def analyze_excel(
    file: Optional[UploadFile] = File(None),
    doc_id: Optional[str] = Form(None, description="文档ID（从数据库读取）"),
    user_prompt: str = Query("", description="用户自定义提示词"),
    analysis_type: str = Query("general", description="分析类型: general, summary, statistics, insights"),
    parse_all_sheets: bool = Query(False, description="是否分析所有工作表")
):
    """
    上传并使用 AI 分析 Excel 文件

    Args:
        file: 上传的 Excel 文件（与 doc_id 二选一）
        doc_id: 文档ID（从数据库读取）
        user_prompt: 用户自定义提示词
        analysis_type: 分析类型
        parse_all_sheets: 是否分析所有工作表

    Returns:
        dict: 分析结果，包含 Excel 数据和 AI 分析结果
    """
    filename = None

    # 从数据库读取模式
    if doc_id:
        try:
            from app.core.database.mongodb import mongodb
            doc = await mongodb.get_document(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"文档不存在: {doc_id}")

            filename = doc.get("metadata", {}).get("original_filename", "unknown.xlsx")
            file_ext = filename.split('.')[-1].lower()

            if file_ext not in ['xlsx', 'xls']:
                raise HTTPException(status_code=400, detail=f"文档类型不是 Excel: {file_ext}")

            file_path = doc.get("metadata", {}).get("file_path")
            if not file_path:
                raise HTTPException(status_code=400, detail="文档没有存储文件路径，请重新上传")

            # 使用文件路径进行 AI 分析
            if parse_all_sheets:
                result = await excel_ai_service.batch_analyze_sheets_from_path(
                    file_path=file_path,
                    filename=filename,
                    user_prompt=user_prompt,
                    analysis_type=analysis_type
                )
            else:
                result = await excel_ai_service.analyze_excel_file_from_path(
                    file_path=file_path,
                    filename=filename,
                    user_prompt=user_prompt,
                    analysis_type=analysis_type
                )

            if result.get("success"):
                return result
            else:
                return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"从数据库读取 Excel 文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")

    # 文件上传模式
    if not file:
        raise HTTPException(status_code=400, detail="请提供文件或文档ID")

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

        # 验证文件内容不为空
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空，请确保文件已正确上传")

        logger.info(f"开始分析文件: {file.filename}, 分析类型: {analysis_type}, 文件大小: {len(content)} bytes")

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
    file: Optional[UploadFile] = File(None),
    doc_id: Optional[str] = Form(None, description="文档ID（从数据库读取）"),
    analysis_type: str = Query("summary", description="分析类型: summary, outline, key_points, questions, tags, qa, statistics, section, charts"),
    user_prompt: str = Query("", description="用户自定义提示词"),
    section_number: Optional[str] = Query(None, description="指定章节编号，如 '一' 或 '（一）'")
):
    """
    上传并使用 AI 分析 Markdown 文件

    Args:
        file: 上传的 Markdown 文件（与 doc_id 二选一）
        doc_id: 文档ID（从数据库读取）
        analysis_type: 分析类型
        user_prompt: 用户自定义提示词
        section_number: 指定分析的章节编号

    Returns:
        dict: 分析结果
    """
    filename = None
    tmp_path = None

    # 验证分析类型
    supported_types = markdown_ai_service.get_supported_analysis_types()
    if analysis_type not in supported_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的分析类型: {analysis_type}，支持的类型: {', '.join(supported_types)}"
        )

    if doc_id:
        # 从数据库读取文档
        try:
            from app.core.database.mongodb import mongodb
            doc = await mongodb.get_document(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"文档不存在: {doc_id}")

            filename = doc.get("metadata", {}).get("original_filename", "unknown.md")
            file_ext = filename.split('.')[-1].lower()

            if file_ext not in ['md', 'markdown']:
                raise HTTPException(status_code=400, detail=f"文档类型不是 Markdown: {file_ext}")

            content = doc.get("content") or ""
            if not content:
                raise HTTPException(status_code=400, detail="文档内容为空")

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.md', delete=False) as tmp:
                tmp.write(content.encode('utf-8'))
                tmp_path = tmp.name

            logger.info(f"从数据库加载 Markdown 文档: {filename}, 长度: {len(content)}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"从数据库读取 Markdown 文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")
    else:
        # 文件上传模式
        if not file:
            raise HTTPException(status_code=400, detail="请提供文件或文档ID")

        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名为空")

        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['md', 'markdown']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，仅支持 .md 和 .markdown"
            )

        try:
            # 读取文件内容
            content = await file.read()

            # 保存到临时文件
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.md', delete=False) as tmp:
                tmp.write(content)
                tmp_path = tmp.name

            filename = file.filename

        except Exception as e:
            logger.error(f"读取 Markdown 文件失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")

    try:
        logger.info(f"开始分析 Markdown 文件: {filename}, 分析类型: {analysis_type}, 章节: {section_number}")

        # 调用 AI 分析服务
        result = await markdown_ai_service.analyze_markdown(
            file_path=tmp_path,
            analysis_type=analysis_type,
            user_prompt=user_prompt,
            section_number=section_number
        )

        logger.info(f"Markdown 分析完成: {filename}, 成功: {result['success']}")

        if not result['success']:
            raise HTTPException(status_code=500, detail=result.get('error', '分析失败'))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Markdown AI 分析过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
    finally:
        # 清理临时文件
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except Exception as cleanup_error:
                logger.warning(f"临时文件清理失败: {tmp_path}, error: {cleanup_error}")


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


@router.post("/analyze/txt")
async def analyze_txt(
    file: Optional[UploadFile] = File(None),
    doc_id: Optional[str] = Form(None, description="文档ID（从数据库读取）"),
    analysis_type: str = Query("structured", description="分析类型: structured, charts")
):
    """
    上传并使用 AI 分析 TXT 文本文件，提取结构化数据或生成图表

    将非结构化文本转换为结构化表格数据，便于后续填表使用
    当 analysis_type=charts 时，可生成可视化图表

    Args:
        file: 上传的 TXT 文件（与 doc_id 二选一）
        doc_id: 文档ID（从数据库读取）
        analysis_type: 分析类型 - "structured"（默认，提取结构化数据）或 "charts"（生成图表）

    Returns:
        dict: 分析结果，包含结构化表格数据或图表数据
    """
    filename = None
    text_content = None

    if doc_id:
        # 从数据库读取文档
        try:
            from app.core.database.mongodb import mongodb
            doc = await mongodb.get_document(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"文档不存在: {doc_id}")

            filename = doc.get("metadata", {}).get("original_filename", "unknown.txt")
            file_ext = filename.split('.')[-1].lower()

            if file_ext not in ['txt', 'text']:
                raise HTTPException(status_code=400, detail=f"文档类型不是 TXT: {file_ext}")

            # 使用数据库中的 content
            text_content = doc.get("content") or ""

            if not text_content:
                raise HTTPException(status_code=400, detail="文档内容为空")

            logger.info(f"从数据库加载 TXT 文档: {filename}, 长度: {len(text_content)}")

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"从数据库读取 TXT 文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")
    else:
        # 文件上传模式
        if not file:
            raise HTTPException(status_code=400, detail="请提供文件或文档ID")

        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名为空")

        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in ['txt', 'text']:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件类型: {file_ext}，仅支持 .txt"
            )

        # 读取文件内容
        content = await file.read()
        text_content = content.decode('utf-8', errors='replace')
        filename = file.filename

    try:
        logger.info(f"开始 AI 分析 TXT 文件: {filename}, analysis_type={analysis_type}")

        # 使用 txt_ai_service 的 AI 分析方法
        result = await txt_ai_service.analyze_txt_with_ai(
            content=text_content,
            filename=filename,
            analysis_type=analysis_type
        )

        if result:
            logger.info(f"TXT AI 分析成功: {filename}")
            return {
                "success": result.get("success", True),
                "filename": filename,
                "analysis_type": analysis_type,
                "result": result
            }
        else:
            logger.warning(f"TXT AI 分析返回空结果: {filename}")
            return {
                "success": False,
                "filename": filename,
                "error": "AI 分析未能提取到结构化数据",
                "result": None
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TXT AI 分析过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


# ==================== Word 文档 AI 解析 ====================

@router.post("/analyze/word")
async def analyze_word(
    file: Optional[UploadFile] = File(None),
    doc_id: Optional[str] = Form(None, description="文档ID（从数据库读取）"),
    user_hint: str = Form("", description="用户提示词，如'请提取表格数据'"),
    analysis_type: str = Query("structured", description="分析类型: structured, charts")
):
    """
    使用 AI 解析 Word 文档，提取结构化数据或生成图表

    适用于从非结构化的 Word 文档中提取表格数据、键值对等信息
    当 analysis_type=charts 时，可生成可视化图表

    Args:
        file: 上传的 Word 文件（与 doc_id 二选一）
        doc_id: 文档ID（从数据库读取）
        user_hint: 用户提示词
        analysis_type: 分析类型 - "structured"（默认，提取结构化数据）或 "charts"（生成图表）

    Returns:
        dict: 包含结构化数据的解析结果或图表数据
    """
    # 获取文件名和扩展名
    filename = None
    file_ext = None

    if doc_id:
        # 从数据库读取文档
        try:
            from app.core.database.mongodb import mongodb
            doc = await mongodb.get_document(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"文档不存在: {doc_id}")

            filename = doc.get("metadata", {}).get("original_filename", "unknown.docx")
            file_ext = filename.split('.')[-1].lower()

            if file_ext not in ['docx']:
                raise HTTPException(status_code=400, detail=f"文档类型不是 Word: {file_ext}")

            # 使用数据库中的 content 进行分析
            content = doc.get("content", "") or ""
            structured_data = doc.get("structured_data") or {}
            tables = structured_data.get("tables", [])

            # 调用 AI 分析服务，传入数据库内容
            if analysis_type == "charts":
                result = await word_ai_service.generate_charts_from_db(
                    content=content,
                    tables=tables,
                    filename=filename,
                    user_hint=user_hint
                )
            else:
                result = await word_ai_service.parse_word_with_ai_from_db(
                    content=content,
                    tables=tables,
                    filename=filename,
                    user_hint=user_hint or "请提取文档中的所有结构化数据，包括表格、键值对等"
                )

            if result.get("success"):
                return {
                    "success": True,
                    "filename": filename,
                    "analysis_type": analysis_type,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "filename": filename,
                    "error": result.get("error", "AI 解析失败"),
                    "result": None
                }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"从数据库读取 Word 文档失败: {str(e)}")
            raise HTTPException(status_code=500, detail=f"读取文档失败: {str(e)}")

    # 文件上传模式
    if not file:
        raise HTTPException(status_code=400, detail="请提供文件或文档ID")

    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['docx']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 .docx"
        )

    try:
        # 保存上传的文件
        content = await file.read()
        suffix = f".{file_ext}"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            # 根据 analysis_type 选择处理方式
            if analysis_type == "charts":
                # 生成图表
                result = await word_ai_service.generate_charts(
                    file_path=tmp_path,
                    user_hint=user_hint
                )
            else:
                # 提取结构化数据
                result = await word_ai_service.parse_word_with_ai(
                    file_path=tmp_path,
                    user_hint=user_hint or "请提取文档中的所有结构化数据，包括表格、键值对等"
                )

            if result.get("success"):
                return {
                    "success": True,
                    "filename": file.filename,
                    "analysis_type": analysis_type,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "filename": file.filename,
                    "error": result.get("error", "AI 解析失败"),
                    "result": None
                }

        finally:
            # 清理临时文件
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Word AI 分析过程中出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
