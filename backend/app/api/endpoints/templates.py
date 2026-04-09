"""
表格模板 API 接口

提供模板上传、解析和填写功能
"""
import io
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, BackgroundTasks
from fastapi.responses import StreamingResponse
import pandas as pd
from pydantic import BaseModel

from app.services.template_fill_service import template_fill_service, TemplateField
from app.services.file_service import file_service
from app.core.database import mongodb
from app.core.document_parser import ParserFactory

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/templates", tags=["表格模板"])


# ==================== 请求/响应模型 ====================

class TemplateFieldRequest(BaseModel):
    """模板字段请求"""
    cell: str
    name: str
    field_type: str = "text"
    required: bool = True
    hint: str = ""


class FillRequest(BaseModel):
    """填写请求"""
    template_id: str
    template_fields: List[TemplateFieldRequest]
    source_doc_ids: Optional[List[str]] = None  # MongoDB 文档 ID 列表
    source_file_paths: Optional[List[str]] = None  # 源文档文件路径列表
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
            "template_id": saved_path,
            "filename": file.filename,
            "file_type": file_ext,
            "fields": [
                {
                    "cell": f.cell,
                    "name": f.name,
                    "field_type": f.field_type,
                    "required": f.required,
                    "hint": f.hint
                }
                for f in template_fields
            ],
            "field_count": len(template_fields)
        }

    except Exception as e:
        logger.error(f"上传模板失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/upload-joint")
async def upload_joint_template(
    background_tasks: BackgroundTasks,
    template_file: UploadFile = File(..., description="模板文件"),
    source_files: List[UploadFile] = File(..., description="源文档文件列表"),
):
    """
    联合上传模板和源文档，一键完成解析和存储

    1. 保存模板文件并提取字段
    2. 异步处理源文档（解析+存MongoDB）
    3. 返回模板信息和源文档ID列表

    Args:
        template_file: 模板文件 (xlsx/xls/docx)
        source_files: 源文档列表 (docx/xlsx/md/txt)

    Returns:
        模板ID、字段列表、源文档ID列表
    """
    if not template_file.filename:
        raise HTTPException(status_code=400, detail="模板文件名为空")

    # 验证模板格式
    template_ext = template_file.filename.split('.')[-1].lower()
    if template_ext not in ['xlsx', 'xls', 'docx']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的模板格式: {template_ext}，仅支持 xlsx/xls/docx"
        )

    # 验证源文档格式
    valid_exts = ['docx', 'xlsx', 'xls', 'md', 'txt']
    for sf in source_files:
        if sf.filename:
            sf_ext = sf.filename.split('.')[-1].lower()
            if sf_ext not in valid_exts:
                raise HTTPException(
                    status_code=400,
                    detail=f"不支持的源文档格式: {sf_ext}，仅支持 docx/xlsx/xls/md/txt"
                )

    try:
        # 1. 保存模板文件
        template_content = await template_file.read()
        template_path = file_service.save_uploaded_file(
            template_content,
            template_file.filename,
            subfolder="templates"
        )

        # 2. 保存并解析源文档 - 提取内容用于生成表头
        source_file_info = []
        source_contents = []
        for sf in source_files:
            if sf.filename:
                sf_content = await sf.read()
                sf_ext = sf.filename.split('.')[-1].lower()
                sf_path = file_service.save_uploaded_file(
                    sf_content,
                    sf.filename,
                    subfolder=sf_ext
                )
                source_file_info.append({
                    "path": sf_path,
                    "filename": sf.filename,
                    "ext": sf_ext
                })
                # 解析源文档获取内容（用于 AI 生成表头）
                try:
                    from app.core.document_parser import ParserFactory
                    parser = ParserFactory.get_parser(sf_path)
                    parse_result = parser.parse(sf_path)
                    if parse_result.success and parse_result.data:
                        source_contents.append({
                            "filename": sf.filename,
                            "doc_type": sf_ext,
                            "content": parse_result.data.get("content", "")[:5000] if parse_result.data.get("content") else "",
                            "titles": parse_result.data.get("titles", [])[:10] if parse_result.data.get("titles") else [],
                            "tables_count": len(parse_result.data.get("tables", [])) if parse_result.data.get("tables") else 0
                        })
                except Exception as e:
                    logger.warning(f"解析源文档失败 {sf.filename}: {e}")

        # 3. 根据源文档内容生成表头
        template_fields = await template_fill_service.get_template_fields_from_file(
            template_path,
            template_ext,
            source_contents=source_contents  # 传递源文档内容
        )

        # 3. 异步处理源文档到MongoDB
        task_id = str(uuid.uuid4())
        if source_file_info:
            background_tasks.add_task(
                process_source_documents,
                task_id=task_id,
                files=source_file_info
            )

        logger.info(f"联合上传完成: 模板={template_file.filename}, 源文档={len(source_file_info)}个")

        return {
            "success": True,
            "template_id": template_path,
            "filename": template_file.filename,
            "file_type": template_ext,
            "fields": [
                {
                    "cell": f.cell,
                    "name": f.name,
                    "field_type": f.field_type,
                    "required": f.required,
                    "hint": f.hint
                }
                for f in template_fields
            ],
            "field_count": len(template_fields),
            "source_file_paths": [f["path"] for f in source_file_info],
            "source_filenames": [f["filename"] for f in source_file_info],
            "task_id": task_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"联合上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"联合上传失败: {str(e)}")


async def process_source_documents(task_id: str, files: List[dict]):
    """异步处理源文档，存入MongoDB"""
    from app.core.database import redis_db

    try:
        await redis_db.set_task_status(
            task_id, status="processing",
            meta={"progress": 0, "message": "开始处理源文档"}
        )

        doc_ids = []
        for i, file_info in enumerate(files):
            try:
                parser = ParserFactory.get_parser(file_info["path"])
                result = parser.parse(file_info["path"])

                if result.success:
                    doc_id = await mongodb.insert_document(
                        doc_type=file_info["ext"],
                        content=result.data.get("content", ""),
                        metadata={
                            **result.metadata,
                            "original_filename": file_info["filename"],
                            "file_path": file_info["path"]
                        },
                        structured_data=result.data.get("structured_data")
                    )
                    doc_ids.append(doc_id)
                    logger.info(f"源文档处理成功: {file_info['filename']}, doc_id: {doc_id}")
                else:
                    logger.error(f"源文档解析失败: {file_info['filename']}, error: {result.error}")

            except Exception as e:
                logger.error(f"源文档处理异常: {file_info['filename']}, error: {str(e)}")

            progress = int((i + 1) / len(files) * 100)
            await redis_db.set_task_status(
                task_id, status="processing",
                meta={"progress": progress, "message": f"已处理 {i+1}/{len(files)}"}
            )

        await redis_db.set_task_status(
            task_id, status="success",
            meta={"progress": 100, "message": "源文档处理完成", "doc_ids": doc_ids}
        )
        logger.info(f"所有源文档处理完成: {len(doc_ids)}个")

    except Exception as e:
        logger.error(f"源文档批量处理失败: {str(e)}")
        await redis_db.set_task_status(
            task_id, status="failure",
            meta={"error": str(e)}
        )


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
                    "required": f.required,
                    "hint": f.hint
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

    根据提供的字段定义，从源文档中检索信息并填写

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
                required=f.required,
                hint=f.hint
            )
            for f in request.template_fields
        ]

        # 执行填写
        result = await template_fill_service.fill_template(
            template_fields=fields,
            source_doc_ids=request.source_doc_ids,
            source_file_paths=request.source_file_paths,
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

    支持 Excel (.xlsx) 和 Word (.docx) 格式

    Args:
        request: 导出请求

    Returns:
        文件流
    """
    try:
        if request.format == "xlsx":
            return await _export_to_excel(request.filled_data, request.template_id)
        elif request.format == "docx":
            return await _export_to_word(request.filled_data, request.template_id)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {request.format}，仅支持 xlsx/docx"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"导出失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")


async def _export_to_excel(filled_data: dict, template_id: str) -> StreamingResponse:
    """导出为 Excel 格式（支持多行）"""
    import logging
    logger = logging.getLogger(__name__)

    logger.info(f"导出填表数据: {len(filled_data)} 个字段")

    # 计算最大行数
    max_rows = 1
    for k, v in filled_data.items():
        if isinstance(v, list) and len(v) > max_rows:
            max_rows = len(v)
        logger.info(f"  {k}: {type(v).__name__} = {str(v)[:80]}")

    logger.info(f"最大行数: {max_rows}")

    # 构建多行数据
    rows_data = []
    for row_idx in range(max_rows):
        row = {}
        for col_name, values in filled_data.items():
            if isinstance(values, list):
                # 取对应行的值，不足则填空
                row[col_name] = values[row_idx] if row_idx < len(values) else ""
            else:
                # 非列表，整个值填入第一行
                row[col_name] = values if row_idx == 0 else ""
        rows_data.append(row)

    df = pd.DataFrame(rows_data)

    # 确保列顺序
    if not df.empty:
        df = df[list(filled_data.keys())]

    logger.info(f"DataFrame 形状: {df.shape}")
    logger.info(f"DataFrame 列: {list(df.columns)}")

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='填写结果')

    output.seek(0)

    filename = f"filled_template.xlsx"

    return StreamingResponse(
        io.BytesIO(output.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


async def _export_to_word(filled_data: dict, template_id: str) -> StreamingResponse:
    """导出为 Word 格式"""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()

    # 添加标题
    title = doc.add_heading('填写结果', level=1)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER

    # 添加填写时间和模板信息
    from datetime import datetime
    info_para = doc.add_paragraph()
    info_para.add_run(f"模板ID: {template_id}\n").bold = True
    info_para.add_run(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    doc.add_paragraph()  # 空行

    # 添加字段表格
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Light Grid Accent 1'

    # 表头
    header_cells = table.rows[0].cells
    header_cells[0].text = '字段名'
    header_cells[1].text = '填写值'
    header_cells[2].text = '状态'

    for field_name, field_value in filled_data.items():
        row_cells = table.add_row().cells
        row_cells[0].text = field_name
        row_cells[1].text = str(field_value) if field_value else ''
        row_cells[2].text = '已填写' if field_value else '为空'

    # 保存到 BytesIO
    output = io.BytesIO()
    doc.save(output)
    output.seek(0)

    filename = f"filled_template.docx"

    return StreamingResponse(
        io.BytesIO(output.getvalue()),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/export/excel")
async def export_to_excel(
    filled_data: dict,
    template_id: str = Query(..., description="模板ID")
):
    """
    专门导出为 Excel 格式

    Args:
        filled_data: 填写数据
        template_id: 模板ID

    Returns:
        Excel 文件流
    """
    return await _export_to_excel(filled_data, template_id)


@router.post("/export/word")
async def export_to_word(
    filled_data: dict,
    template_id: str = Query(..., description="模板ID")
):
    """
    专门导出为 Word 格式

    Args:
        filled_data: 填写数据
        template_id: 模板ID

    Returns:
        Word 文件流
    """
    return await _export_to_word(filled_data, template_id)
