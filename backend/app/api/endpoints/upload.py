"""
文件上传 API 接口
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import pandas as pd
import io

from app.services.file_service import file_service
from app.core.document_parser import XlsxParser
from app.services.table_rag_service import table_rag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["文件上传"])

# 初始化解析器
excel_parser = XlsxParser()


@router.post("/excel")
async def upload_excel(
    file: UploadFile = File(...),
    parse_all_sheets: bool = Query(False, description="是否解析所有工作表"),
    sheet_name: Optional[str] = Query(None, description="指定解析的工作表名称"),
    header_row: int = Query(0, description="表头所在的行索引")
):
    """
    上传并解析 Excel 文件，同时存储到 MySQL 数据库

    Args:
        file: 上传的 Excel 文件
        parse_all_sheets: 是否解析所有工作表
        sheet_name: 指定解析的工作表名称
        header_row: 表头所在的行索引

    Returns:
        dict: 解析结果
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

    try:
        # 读取文件内容
        content = await file.read()

        # 保存文件
        saved_path = file_service.save_uploaded_file(
            content,
            file.filename,
            subfolder="excel"
        )

        logger.info(f"文件已保存: {saved_path}")

        # 解析文件
        if parse_all_sheets:
            result = excel_parser.parse_all_sheets(saved_path)
        else:
            # 如果指定了 sheet_name，使用指定的，否则使用默认的第一个
            if sheet_name:
                result = excel_parser.parse(saved_path, sheet_name=sheet_name, header_row=header_row)
            else:
                result = excel_parser.parse(saved_path, header_row=header_row)

        # 添加文件路径到元数据
        if result.metadata:
            result.metadata['saved_path'] = saved_path
            result.metadata['original_filename'] = file.filename

        # 存储到 MySQL 数据库
        try:
            store_result = await table_rag_service.build_table_rag_index(
                file_path=saved_path,
                filename=file.filename,
                sheet_name=sheet_name if sheet_name else None,
                header_row=header_row
            )
            if store_result.get("success"):
                result.metadata['mysql_table'] = store_result.get('table_name')
                result.metadata['row_count'] = store_result.get('row_count')
                logger.info(f"Excel已存储到MySQL: {file.filename}, 表: {store_result.get('table_name')}")
            else:
                logger.warning(f"Excel存储到MySQL失败: {store_result.get('error')}")
        except Exception as e:
            logger.error(f"Excel存储到MySQL异常: {str(e)}", exc_info=True)

        return result.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析 Excel 文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"解析失败: {str(e)}")


@router.get("/excel/preview/{file_path:path}")
async def get_excel_preview(
    file_path: str,
    sheet_name: Optional[str] = Query(None, description="工作表名称"),
    max_rows: int = Query(10, description="最多返回的行数", ge=1, le=100)
):
    """
    获取 Excel 文件的预览数据

    Args:
        file_path: 文件路径
        sheet_name: 工作表名称
        max_rows: 最多返回的行数

    Returns:
        dict: 预览数据
    """
    try:
        # 解析工作表名称参数
        sheet_param = sheet_name if sheet_name else 0

        result = excel_parser.get_sheet_preview(
            file_path,
            sheet_name=sheet_param,
            max_rows=max_rows
        )

        return result.to_dict()

    except Exception as e:
        logger.error(f"获取预览数据时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取预览失败: {str(e)}")


@router.delete("/file")
async def delete_uploaded_file(file_path: str = Query(..., description="要删除的文件路径")):
    """
    删除已上传的文件

    Args:
        file_path: 文件路径

    Returns:
        dict: 删除结果
    """
    try:
        success = file_service.delete_file(file_path)

        if success:
            return {"success": True, "message": "文件删除成功"}
        else:
            return {"success": False, "message": "文件不存在或删除失败"}

    except Exception as e:
        logger.error(f"删除文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@router.get("/excel/export/{file_path:path}")
async def export_excel(
    file_path: str,
    sheet_name: Optional[str] = Query(None, description="工作表名称"),
    columns: Optional[str] = Query(None, description="要导出的列，逗号分隔")
):
    """
    导出 Excel 文件（可选择工作表和列）

    Args:
        file_path: 原始文件路径
        sheet_name: 工作表名称（可选）
        columns: 要导出的列名，逗号分隔（可选）

    Returns:
        StreamingResponse: Excel 文件
    """
    try:
        # 读取 Excel 文件
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            df = pd.read_excel(file_path)

        # 如果指定了列，只选择这些列
        if columns:
            column_list = [col.strip() for col in columns.split(',')]
            # 过滤掉不存在的列
            available_columns = [col for col in column_list if col in df.columns]
            if available_columns:
                df = df[available_columns]

        # 创建 Excel 文件
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name=sheet_name or 'Sheet1')

        output.seek(0)

        # 生成文件名
        original_name = file_path.split('/')[-1] if '/' in file_path else file_path
        if columns:
            export_name = f"export_{sheet_name or 'data'}_{len(column_list) if columns else 'all'}_cols.xlsx"
        else:
            export_name = f"export_{original_name}"

        # 返回文件流
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={export_name}"}
        )

    except FileNotFoundError:
        logger.error(f"文件不存在: {file_path}")
        raise HTTPException(status_code=404, detail="文件不存在")
    except Exception as e:
        logger.error(f"导出 Excel 文件时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"导出失败: {str(e)}")
