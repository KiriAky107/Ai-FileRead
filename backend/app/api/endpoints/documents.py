"""
文档管理 API 接口

支持多格式文档(docx/xlsx/md/txt)上传、解析、存储和RAG索引
集成 Excel 存储和 AI 生成字段描述
"""
import asyncio
import logging
import uuid
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel

from app.services.file_service import file_service
from app.core.database import mongodb, redis_db
from app.services.rag_service import rag_service
from app.services.table_rag_service import table_rag_service
from app.services.excel_storage_service import excel_storage_service
from app.core.document_parser import ParserFactory, ParseResult

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["文档上传"])


# ==================== 辅助函数 ====================

async def update_task_status(
    task_id: str,
    status: str,
    progress: int = 0,
    message: str = "",
    result: dict = None,
    error: str = None
):
    """
    更新任务状态，同时写入 Redis 和 MongoDB

    Args:
        task_id: 任务ID
        status: 状态
        progress: 进度
        message: 消息
        result: 结果
        error: 错误信息
    """
    meta = {"progress": progress, "message": message}
    if result:
        meta["result"] = result
    if error:
        meta["error"] = error

    # 尝试写入 Redis
    try:
        await redis_db.set_task_status(task_id, status, meta)
    except Exception as e:
        logger.warning(f"Redis 任务状态更新失败: {e}")

    # 尝试写入 MongoDB（作为备用）
    try:
        await mongodb.update_task(
            task_id=task_id,
            status=status,
            message=message,
            result=result,
            error=error
        )
    except Exception as e:
        logger.warning(f"MongoDB 任务状态更新失败: {e}")


# ==================== 请求/响应模型 ====================

class UploadResponse(BaseModel):
    task_id: str
    file_count: int
    message: str
    status_url: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: int = 0
    message: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None


# ==================== 文档上传接口 ====================

@router.post("/document", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
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
    4. 如果是 Excel：
       - 存入 MySQL (结构化数据)
       - AI 生成字段描述
       - 建立 RAG 索引
    5. 建立 RAG 索引 (非结构化文档)
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名为空")

    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in ['docx', 'xlsx', 'xls', 'md', 'txt']:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，仅支持 docx/xlsx/xls/md/txt"
        )

    task_id = str(uuid.uuid4())

    try:
        # 保存任务记录到 MongoDB（如果 Redis 不可用时仍能查询）
        try:
            await mongodb.insert_task(
                task_id=task_id,
                task_type="document_parse",
                status="pending",
                message=f"文档 {file.filename} 已提交处理"
            )
        except Exception as mongo_err:
            logger.warning(f"MongoDB 保存任务记录失败: {mongo_err}")

        content = await file.read()
        saved_path = file_service.save_uploaded_file(
            content,
            file.filename,
            subfolder=file_ext
        )

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
):
    """批量上传文档"""
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    task_id = str(uuid.uuid4())
    saved_paths = []

    try:
        # 保存任务记录到 MongoDB
        try:
            await mongodb.insert_task(
                task_id=task_id,
                task_type="batch_parse",
                status="pending",
                message=f"已提交 {len(files)} 个文档处理"
            )
        except Exception as mongo_err:
            logger.warning(f"MongoDB 保存批量任务记录失败: {mongo_err}")

        for file in files:
            if not file.filename:
                continue
            content = await file.read()
            saved_path = file_service.save_uploaded_file(content, file.filename, subfolder="batch")
            saved_paths.append({
                "path": saved_path,
                "filename": file.filename,
                "ext": file.filename.split('.')[-1].lower()
            })

        background_tasks.add_task(process_documents_batch, task_id=task_id, files=saved_paths)

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
    try:
        # 状态: 解析中
        await update_task_status(
            task_id, status="processing",
            progress=10, message="正在解析文档"
        )

        # 解析文档
        parser = ParserFactory.get_parser(file_path)
        result = parser.parse(file_path)

        if not result.success:
            raise Exception(result.error or "解析失败")

        # 状态: 存储中
        await update_task_status(
            task_id, status="processing",
            progress=30, message="正在存储数据"
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

        # 如果是 Excel，存储到 MySQL + AI生成描述 + RAG索引
        mysql_table_name = None
        if doc_type in ["xlsx", "xls"]:
            await update_task_status(
                task_id, status="processing",
                progress=50, message="正在存储到MySQL并生成字段描述"
            )

            try:
                # 使用 TableRAG 服务存储到 MySQL（跳过 RAG 索引以提升速度）
                logger.info(f"开始存储Excel到MySQL: {original_filename}, file_path: {file_path}")
                rag_result = await table_rag_service.build_table_rag_index(
                    file_path=file_path,
                    filename=original_filename,
                    sheet_name=parse_options.get("sheet_name"),
                    header_row=parse_options.get("header_row", 0),
                    skip_rag_index=True  # 跳过 AI 字段描述生成和索引
                )

                if rag_result.get("success"):
                    mysql_table_name = rag_result.get('table_name')
                    logger.info(f"Excel存储到MySQL成功: {original_filename}, table: {mysql_table_name}")
                    # 更新 MongoDB 中的 metadata，记录 MySQL 表名
                    try:
                        doc = await mongodb.get_document(doc_id)
                        if doc:
                            metadata = doc.get("metadata", {})
                            metadata["mysql_table_name"] = mysql_table_name
                            await mongodb.update_document_metadata(doc_id, metadata)
                            logger.info(f"已更新 MongoDB 文档的 mysql_table_name: {mysql_table_name}")
                    except Exception as update_err:
                        logger.warning(f"更新 MongoDB mysql_table_name 失败: {update_err}")
                else:
                    logger.error(f"RAG索引构建失败: {rag_result.get('error')}")
            except Exception as e:
                logger.error(f"Excel存储到MySQL异常: {str(e)}", exc_info=True)

        else:
            # 非结构化文档
            structured_data = result.data.get("structured_data", {})
            tables = structured_data.get("tables", [])

            # 如果文档中有表格数据，提取并存储到 MySQL（不需要 RAG 索引）
            if tables:
                await update_task_status(
                    task_id, status="processing",
                    progress=60, message="正在存储表格数据"
                )
                # 对每个表格建立 MySQL 表（跳过 RAG 索引，速度更快）
                for table_info in tables:
                    await table_rag_service.index_document_table(
                        doc_id=doc_id,
                        filename=original_filename,
                        table_data=table_info,
                        source_doc_type=doc_type
                    )

            # 对文档内容建立 RAG 索引（非结构化文本需要语义搜索）
            content = result.data.get("content", "")
            if content and len(content) > 50:  # 只有内容足够长才建立索引
                await update_task_status(
                    task_id, status="processing",
                    progress=80, message="正在建立语义索引"
                )
                await index_document_to_rag(doc_id, original_filename, result, doc_type)

        # 完成
        await update_task_status(
            task_id, status="success",
            progress=100, message="处理完成",
            result={
                "doc_id": doc_id,
                "doc_type": doc_type,
                "filename": original_filename
            }
        )

        logger.info(f"文档处理完成: {original_filename}, doc_id: {doc_id}")

    except Exception as e:
        logger.error(f"文档处理失败: {str(e)}")
        await update_task_status(
            task_id, status="failure",
            progress=0, message="处理失败",
            error=str(e)
        )


async def process_documents_batch(task_id: str, files: List[dict]):
    """批量并行处理文档"""
    try:
        await update_task_status(
            task_id, status="processing",
            progress=0, message=f"开始批量处理 {len(files)} 个文档",
            result={"total": len(files), "files": []}
        )

        async def process_single_file(file_info: dict, index: int) -> dict:
            """处理单个文件"""
            filename = file_info["filename"]
            try:
                # 解析文档
                parser = ParserFactory.get_parser(file_info["path"])
                result = parser.parse(file_info["path"])

                if not result.success:
                    return {"index": index, "filename": filename, "success": False, "error": result.error or "解析失败"}

                # 存储到 MongoDB
                doc_id = await mongodb.insert_document(
                    doc_type=file_info["ext"],
                    content=result.data.get("content", ""),
                    metadata={
                        **result.metadata,
                        "original_filename": filename,
                        "file_path": file_info["path"]
                    },
                    structured_data=result.data.get("structured_data")
                )

                # Excel 处理
                if file_info["ext"] in ["xlsx", "xls"]:
                    await table_rag_service.build_table_rag_index(
                        file_path=file_info["path"],
                        filename=filename,
                        skip_rag_index=True  # 跳过 AI 字段描述生成和索引
                    )
                else:
                    # 非结构化文档
                    structured_data = result.data.get("structured_data", {})
                    tables = structured_data.get("tables", [])

                    # 表格数据直接存 MySQL（跳过 RAG 索引）
                    if tables:
                        for table_info in tables:
                            await table_rag_service.index_document_table(
                                doc_id=doc_id,
                                filename=filename,
                                table_data=table_info,
                                source_doc_type=file_info["ext"]
                            )

                    # 只有内容足够长才建立语义索引
                    content = result.data.get("content", "")
                    if content and len(content) > 50:
                        await index_document_to_rag(doc_id, filename, result, file_info["ext"])

                return {"index": index, "filename": filename, "doc_id": doc_id, "file_path": file_info["path"], "success": True}

            except Exception as e:
                logger.error(f"处理文件 {filename} 失败: {e}")
                return {"index": index, "filename": filename, "success": False, "error": str(e)}

        # 并行处理所有文档
        tasks = [process_single_file(f, i) for i, f in enumerate(files)]
        results = await asyncio.gather(*tasks)

        # 按原始顺序排序
        results.sort(key=lambda x: x["index"])

        # 统计成功/失败数量
        success_count = sum(1 for r in results if r["success"])
        fail_count = len(results) - success_count

        # 更新最终状态
        await update_task_status(
            task_id, status="success",
            progress=100, message=f"批量处理完成: {success_count} 成功, {fail_count} 失败",
            result={
                "total": len(files),
                "success": success_count,
                "failure": fail_count,
                "results": results
            }
        )

        logger.info(f"批量处理完成: {success_count}/{len(files)} 成功")

    except Exception as e:
        logger.error(f"批量处理失败: {str(e)}")
        await update_task_status(
            task_id, status="failure",
            progress=0, message="批量处理失败",
            error=str(e)
        )


async def index_document_to_rag(doc_id: str, filename: str, result: ParseResult, doc_type: str):
    """将非结构化文档索引到 RAG（使用分块索引，异步执行）"""
    try:
        content = result.data.get("content", "")
        if content:
            # 使用异步方法索引，避免阻塞事件循环
            await rag_service.index_document_content_async(
                doc_id=doc_id,
                content=content,
                metadata={
                    "filename": filename,
                    "doc_type": doc_type
                },
                chunk_size=1000,  # 每块 1000 字符，提升速度
                chunk_overlap=100  # 块之间 100 字符重叠
            )
            logger.info(f"RAG 索引完成: {filename}, doc_id={doc_id}")
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
