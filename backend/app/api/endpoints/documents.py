"""
文档管理 API 接口

支持多格式文档(docx/xlsx/md/txt)上传、解析、存储和RAG索引
"""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.services.file_service import file_service
from app.core.database import mongodb, mysql_db
from app.services.rag_service import rag_service
from app.core.document_parser import ParserFactory, ParseResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["文档上传"])


# ==================== 请求/响应模型 ====================

class UploadResponse(BaseModel):
    task_id: str
    file_count: int
    message: str
    status_url: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # pending, processing, success, failure
    progress: int = 0
    message: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


# ==================== 文档上传接口 ====================

@router.post("/document", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: Optional[str] = Query(None, description="文档类型: docx/xlsx/md/txt"),
    parse_all_sheets: bool = Query(False, description="是否解析所有工作表(仅Excel)"),
    sheet_name: Optional[str] = Query(None, description="指定工作表(仅Excel)"),
    header_row: int = Query(0, description="表头行号(仅Excel)")
):
    """
    上传单个文档并异步处理

    文档会：
    1. 保存到本地存储
    2. 解析内容
    3. 存入 MongoDB (原始内容)
    4. 如果是 Excel，存入 MySQL (结构化数据)
    5. 建立 RAG 索引
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    # 根据扩展名确定文档类型
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['docx', 'xlsx', 'xls', 'md', 'txt']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 docx/xlsx/xls/md/txt"
        )

    # 生成任务ID
    task_id = str(uuid.uuid4())

    try:
        # 读取文件内容
        content = await file.read()

        # 保存文件
        saved_path = file_service.save_uploaded_file(
            content,
            file.filename,
            subfolder=file_ext
        )

        # 后台处理文档
        background_tasks.add_task(
            process_document,
            task_id=task_id,
            file_path=saved_path,
            original_filename=file.filename,
            doc_type=file_ext,
            parse_options={
                "parse_all_sheets": parse_all_sheets,
                "sheet_name": sheet_name,
                "header_row": header_row
            }
        )

        return UploadResponse(
            task_id=task_id,
            file_count=1,
            message=f"文档 {file.filename} 已提交处理",
            status_url=f"/api/v1/tasks/{task_id}"
        )

    except Exception as e:
        logger.error(f"上传文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/documents", response_model=UploadResponse)
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    doc_type: Optional[str] = Query(None, description="文档类型")
):
    """
    批量上传文档

    所有文档会异步处理，处理完成后可通过 task_id 查询状态
    """
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    task_id = str(uuid.uuid4())
    saved_paths = []

    try:
        for file in files:
            if not file.filename:
                continue

            content = await file.read()
            saved_path = file_service.save_uploaded_file(
                content,
                file.filename,
                subfolder="batch"
            )
            saved_paths.append({
                "path": saved_path,
                "filename": file.filename,
                "ext": file.filename.split('.')[-1].lower()
            })

        # 后台处理所有文档
        background_tasks.add_task(
            process_documents_batch,
            task_id=task_id,
            files=saved_paths
        )

        return UploadResponse(
            task_id=task_id,
            file_count=len(saved_paths),
            message=f"已提交 {len(saved_paths)} 个文档处理",
            status_url=f"/api/v1/tasks/{task_id}"
        )

    except Exception as e:
        logger.error(f"批量上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"批量上传失败: {str(e)}")


# ==================== 任务处理函数 ====================

async def process_document(
    task_id: str,
    file_path: str,
    original_filename: str,
    doc_type: str,
    parse_options: dict
):
    """处理单个文档"""
    from app.core.database import redis_db

    try:
        # 更新状态: 处理中
        await redis_db.set_task_status(
            task_id,
            status="processing",
            meta={"progress": 10, "message": "正在解析文档"}
        )

        # 解析文档
        parser = ParserFactory.get_parser(file_path)
        result = parser.parse(file_path)

        if not result.success:
            raise Exception(result.error or "解析失败")

        # 更新状态: 存储数据
        await redis_db.set_task_status(
            task_id,
            status="processing",
            meta={"progress": 40, "message": "正在存储数据"}
        )

        # 存储到 MongoDB
        doc_id = await mongodb.insert_document(
            doc_type=doc_type,
            content=result.data.get("content", ""),
            metadata={
                **result.metadata,
                "original_filename": original_filename,
                "file_path": file_path
            },
            structured_data=result.data.get("structured_data")
        )

        # 如果是 Excel，存储到 MySQL
        if doc_type in ["xlsx", "xls"]:
            await store_excel_to_mysql(file_path, original_filename, result)

        # 更新状态: 建立 RAG 索引
        await redis_db.set_task_status(
            task_id,
            status="processing",
            meta={"progress": 70, "message": "正在建立索引"}
        )

        # 建立 RAG 索引
        await index_document_to_rag(doc_id, original_filename, result, doc_type)

        # 更新状态: 完成
        await redis_db.set_task_status(
            task_id,
            status="success",
            meta={
                "progress": 100,
                "message": "处理完成",
                "doc_id": doc_id,
                "result": {
                    "doc_id": doc_id,
                    "doc_type": doc_type,
                    "filename": original_filename
                }
            }
        )

        logger.info(f"文档处理完成: {original_filename}, doc_id: {doc_id}")

    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}")
        await redis_db.set_task_status(
            task_id,
            status="failure",
            meta={"error": str(e)}
        )


async def process_documents_batch(task_id: str, files: List[dict]):
    """批量处理文档"""
    from app.core.database import redis_db

    try:
        await redis_db.set_task_status(
            task_id,
            status="processing",
            meta={"progress": 0, "message": "开始批量处理"}
        )

        results = []
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
                    results.append({"filename": file_info["filename"], "doc_id": doc_id, "success": True})
                else:
                    results.append({"filename": file_info["filename"], "success": False, "error": result.error})

            except Exception as e:
                results.append({"filename": file_info["filename"], "success": False, "error": str(e)})

            # 更新进度
            progress = int((i + 1) / len(files) * 100)
            await redis_db.set_task_status(
                task_id,
                status="processing",
                meta={"progress": progress, "message": f"已处理 {i+1}/{len(files)}"}
            )

        await redis_db.set_task_status(
            task_id,
            status="success",
            meta={"progress": 100, "message": "批量处理完成", "results": results}
        )

    except Exception as e:
        logger.error(f"批量处理失败: {str(e)}")
        await redis_db.set_task_status(
            task_id,
            status="failure",
            meta={"error": str(e)}
        )


async def store_excel_to_mysql(file_path: str, filename: str, result: ParseResult):
    """将 Excel 数据存储到 MySQL"""
    # TODO: 实现 Excel 数据到 MySQL 的转换和存储
    # 需要根据表头动态创建表结构
    pass


async def index_document_to_rag(doc_id: str, filename: str, result: ParseResult, doc_type: str):
    """将文档索引到 RAG"""
    try:
        if doc_type in ["xlsx", "xls"]:
            # Excel 文件: 索引字段信息
            columns = result.metadata.get("columns", [])
            for col in columns:
                rag_service.index_field(
                    table_name=filename,
                    field_name=col,
                    field_description=f"Excel表格 {filename} 的列 {col}",
                    sample_values=None
                )
        else:
            # 其他文档: 索引文档内容
            content = result.data.get("content", "")
            if content:
                rag_service.index_document_content(
                    doc_id=doc_id,
                    content=content[:5000],  # 限制长度
                    metadata={
                        "filename": filename,
                        "doc_type": doc_type
                    }
                )
    except Exception as e:
        logger.warning(f"RAG 索引失败: {str(e)}")


# ==================== 文档解析接口 ====================

@router.post("/document/parse")
async def parse_uploaded_document(
    file_path: str = Query(..., description="文件路径")
):
    """解析已上传的文档"""
    try:
        parser = ParserFactory.get_parser(file_path)
        result = parser.parse(file_path)

        if result.success:
            return result.to_dict()
        else:
            raise HTTPException(status_code=400, detail=result.error)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"解析文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


# 需要添加 import
import logging
