"""
表格模板 API 接口

提供模板上传、解析和填写功能
"""
import io
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
import pandas as pd
from pydantic import BaseModel

from app.services.template_fill_service import template_fill_service, TemplateField
from app.services.excel_storage_service import excel_storage_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["表格模板"])


# ==================== 请求/响应模型 ====================

class TemplateFieldRequest(BaseModel):
    """模板字段请求"""
    cell: str
    name: str
    field_type: str = "text"
    required: bool = True


class FillRequest(BaseModel):
    """填写请求"""
    template_id: str
    template_fields: List[TemplateFieldRequest]
    source_doc_ids: Optional[List[str]] = None
    user_hint: Optional[str] = None


class ExportRequest(BaseModel):
    """导出请求"""
    template_id: str
    filled_data: dict
    format: str = "xlsx"  # xlsx 或 docx


# ==================== 接口实现 ====================

@router.post("/upload")
async def upload_template(
    file: UploadFile = File(...),
):
    """
    上传表格模板文件

    支持 Excel (.xlsx, .xls) 和 Word (.docx) 格式

    Returns:
        模板信息，包括提取的字段列表
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['xlsx', 'xls', 'docx']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模板格式: {file_ext}，仅支持 xlsx/xls/docx"
        )

    try:
        # 保存文件
        from app.services.file_service import file_service
        content = await file.read()
        saved_path = file_service.save_uploaded_file(
            content,
            file.filename,
            subfolder="templates"
        )

        # 提取字段
        template_fields = await template_fill_service.get_template_fields_from_file(
            saved_path,
            file_ext
        )

        return {
            "success": True,
            "template_id": saved_path,  # 使用文件路径作为ID
            "filename": file.filename,
            "file_type": file_ext,
            "fields": [
                {
                    "cell": f.cell,
                    "name": f.name,
                    "field_type": f.field_type,
                    "required": f.required
                }
                for f in template_fields
            ],
            "field_count": len(template_fields)
        }

    except Exception as e:
        logger.error(f"上传模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/fields")
async def extract_template_fields(
    template_id: str = Query(..., description="模板ID/文件路径"),
    file_type: str = Query("xlsx", description="文件类型")
):
    """
    从已上传的模板提取字段定义

    Args:
        template_id: 模板ID
        file_type: 文件类型

    Returns:
        字段列表
    """
    try:
        fields = await template_fill_service.get_template_fields_from_file(
            template_id,
            file_type
        )

        return {
            "success": True,
            "fields": [
                {
                    "cell": f.cell,
                    "name": f.name,
                    "field_type": f.field_type,
                    "required": f.required
                }
                for f in fields
            ]
        }

    except Exception as e:
        logger.error(f"提取字段失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"提取失败: {str(e)}")


@router.post("/fill")
async def fill_template(
    request: FillRequest,
):
    """
    执行表格填写

    根据提供的字段定义，从已上传的文档中检索信息并填写

    Args:
        request: 填写请求

    Returns:
        填写结果
    """
    try:
        # 转换字段
        fields = [
            TemplateField(
                cell=f.cell,
                name=f.name,
                field_type=f.field_type,
                required=f.required
            )
            for f in request.template_fields
        ]

        # 执行填写
        result = await template_fill_service.fill_template(
            template_fields=fields,
            source_doc_ids=request.source_doc_ids,
            user_hint=request.user_hint
        )

        return result

    except Exception as e:
        logger.error(f"填写表格失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"填写失败: {str(e)}")


@router.post("/export")
async def export_filled_template(
    request: ExportRequest,
):
    """
    导出填写后的表格

    Args:
        request: 导出请求

    Returns:
        文件流
    """
    try:
        # 创建 DataFrame
        df = pd.DataFrame([request.filled_data])

        # 导出为 Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='填写结果')

        output.seek(0)

        # 生成文件名
        filename = f"filled_template.{request.format}"

        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )

    except Exception as e:
        logger.error(f"导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


# ==================== 需要添加的 import ====================
import logging
