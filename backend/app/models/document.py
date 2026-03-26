"""
文档数据模型

定义文档相关的 Pydantic 模型
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """文档类型枚举"""
    DOCX = "docx"
    XLSX = "xlsx"
    MD = "md"
    TXT = "txt"


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILURE = "failure"


# ==================== 解析结果模型 ====================

class DocumentMetadata(BaseModel):
    """文档元数据"""
    filename: str
    extension: str
    file_size: int = 0
    doc_type: Optional[str] = None
    sheet_count: Optional[int] = None
    sheet_names: Optional[List[str]] = None
    current_sheet: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    columns: Optional[List[str]] = None
    encoding: Optional[str] = None


class ParseResultData(BaseModel):
    """解析结果数据"""
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    column_count: int = 0


class ParseResult(BaseModel):
    """文档解析结果"""
    success: bool
    data: Optional[ParseResultData] = None
    metadata: Optional[DocumentMetadata] = None
    error: Optional[str] = None


# ==================== 存储模型 ====================

class DocumentStore(BaseModel):
    """文档存储模型"""
    doc_id: str
    doc_type: DocumentType
    content: str
    metadata: DocumentMetadata
    structured_data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class RAGEntry(BaseModel):
    """RAG索引条目"""
    table_name: str
    field_name: str
    field_description: str
    embedding: List[float]
    metadata: Optional[Dict[str, Any]] = None


# ==================== 任务模型 ====================

class TaskCreate(BaseModel):
    """任务创建请求"""
    task_type: str
    input_params: Dict[str, Any]


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    status: TaskStatus
    progress: int = 0
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None


# ==================== 模板填写模型 ====================

class TemplateField(BaseModel):
    """模板字段"""
    cell: str = Field(description="单元格位置, 如 A1")
    name: str = Field(description="字段名称")
    field_type: str = Field(default="text", description="字段类型: text/number/date")
    required: bool = Field(default=True, description="是否必填")


class TemplateSheet(BaseModel):
    """模板工作表"""
    name: str
    fields: List[TemplateField]


class TemplateInfo(BaseModel):
    """模板信息"""
    file_path: str
    file_type: str  # xlsx/docx
    sheets: List[TemplateSheet]


class FillRequest(BaseModel):
    """填写请求"""
    template_path: str
    template_fields: List[TemplateField]
    source_doc_ids: Optional[List[str]] = None


class FillResult(BaseModel):
    """填写结果"""
    success: bool
    filled_data: Dict[str, Any]
    fill_details: List[Dict[str, Any]]
    source_documents: List[str] = Field(default_factory=list)


# ==================== API 响应模型 ====================

class UploadResponse(BaseModel):
    """上传响应"""
    task_id: str
    file_count: int
    message: str
    status_url: str


class AnalyzeResponse(BaseModel):
    """分析响应"""
    success: bool
    analysis: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    error: Optional[str] = None


class QueryRequest(BaseModel):
    """查询请求"""
    user_intent: str
    table_name: Optional[str] = None
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    """查询响应"""
    success: bool
    sql_query: Optional[str] = None
    results: Optional[List[Dict[str, Any]]] = None
    rag_context: Optional[List[str]] = None
    error: Optional[str] = None
