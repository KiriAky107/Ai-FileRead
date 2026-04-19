"""
PDF 转换 API 接口

提供将 Word、Excel、Txt、Markdown 转换为 PDF 的功能
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse

from app.services.pdf_converter_service import pdf_converter_service
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf", tags=["PDF转换"])

# 临时存储转换后的 PDF（key: download_id, value: (pdf_content, original_filename)）
_pdf_cache: dict = {}


# ==================== 请求/响应模型 ====================

class ConvertResponse:
    """转换响应"""
    def __init__(self, success: bool, message: str = "", filename: str = ""):
        self.success = success
        self.message = message
        self.filename = filename


# ==================== 接口 ====================

@router.post("/convert")
async def convert_to_pdf(
    file: UploadFile = File(...),
):
    """
    将上传的文件转换为 PDF

    支持格式: docx, xlsx, txt, md

    Args:
        file: 上传的文件

    Returns:
        PDF 文件流
    """
    try:
        # 检查文件格式
        filename = file.filename or "document"
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

        if file_ext not in pdf_converter_service.supported_formats:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的格式: {file_ext}，支持的格式: {', '.join(pdf_converter_service.supported_formats)}"
            )

        # 读取文件内容
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="文件内容为空")

        logger.info(f"开始转换文件: {filename} ({file_ext})")

        # 转换为 PDF
        pdf_content, error = await pdf_converter_service.convert_to_pdf(
            file_content=content,
            source_format=file_ext,
            filename=filename.rsplit('.', 1)[0] if '.' in filename else filename
        )

        if error:
            raise HTTPException(status_code=500, detail=error)

        # 直接返回 PDF 文件流
        return StreamingResponse(
            iter([pdf_content]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''converted.pdf"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"PDF转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"转换失败: {str(e)}")


@router.get("/download/{download_id}")
async def download_pdf(download_id: str):
    """
    通过下载 ID 下载 PDF（支持 IDM 拦截）
    """
    if download_id not in _pdf_cache:
        raise HTTPException(status_code=404, detail="下载链接已过期或不存在")

    pdf_content, filename = _pdf_cache.pop(download_id)  # 下载后删除

    # 使用 RFC 5987 编码支持中文文件名
    from starlette.responses import StreamingResponse
    import urllib.parse

    # URL 编码中文文件名
    encoded_filename = urllib.parse.quote(f"{filename}.pdf")

    return StreamingResponse(
        iter([pdf_content]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )


@router.get("/formats")
async def get_supported_formats():
    """
    获取支持的源文件格式

    Returns:
        支持的格式列表
    """
    return {
        "success": True,
        "formats": pdf_converter_service.get_supported_formats()
    }


@router.post("/convert/batch")
async def batch_convert_to_pdf(
    files: list[UploadFile] = File(...),
):
    """
    批量将多个文件转换为 PDF

    注意: 批量转换会返回多个 PDF 文件打包的 zip

    Args:
        files: 上传的文件列表

    Returns:
        ZIP 压缩包（包含所有PDF）
    """
    try:
        import io
        import zipfile

        results = []
        errors = []

        for file in files:
            try:
                filename = file.filename or "document"
                file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''

                if file_ext not in pdf_converter_service.supported_formats:
                    errors.append(f"{filename}: 不支持的格式")
                    continue

                content = await file.read()
                pdf_content, error = await pdf_converter_service.convert_to_pdf(
                    file_content=content,
                    source_format=file_ext,
                    filename=filename.rsplit('.', 1)[0] if '.' in filename else filename
                )

                if error:
                    errors.append(f"{filename}: {error}")
                else:
                    results.append((filename, pdf_content))

            except Exception as e:
                errors.append(f"{file.filename}: {str(e)}")

        if not results:
            raise HTTPException(
                status_code=400,
                detail=f"没有可转换的文件。错误: {'; '.join(errors)}"
            )

        # 创建 ZIP 包
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for original_name, pdf_content in results:
                pdf_name = f"{original_name.rsplit('.', 1)[0] if '.' in original_name else original_name}.pdf"
                zip_file.writestr(pdf_name, pdf_content)

        zip_buffer.seek(0)

        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={
                "Content-Disposition": "attachment; filename*=UTF-8''converted_pdfs.zip"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量PDF转换失败: {e}")
        raise HTTPException(status_code=500, detail=f"批量转换失败: {str(e)}")
