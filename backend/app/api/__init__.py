"""
API 路由注册模块
"""
from fastapi import APIRouter
from app.api.endpoints import (
    upload,
    documents,      # 多格式文档上传
    tasks,          # 任务管理
    library,        # 文档库
    rag,            # RAG检索
    templates,      # 表格模板
    ai_analyze,
    visualization,
    analysis_charts,
    health,
    instruction,    # 智能指令
    conversation,   # 对话历史
)

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(health.router)           # 健康检查
api_router.include_router(upload.router)            # 原有Excel上传
api_router.include_router(documents.router)        # 多格式文档上传
api_router.include_router(tasks.router)            # 任务状态查询
api_router.include_router(library.router)          # 文档库管理
api_router.include_router(rag.router)              # RAG检索
api_router.include_router(templates.router)        # 表格模板
api_router.include_router(ai_analyze.router)       # AI分析
api_router.include_router(visualization.router)    # 可视化
api_router.include_router(analysis_charts.router)  # 分析图表
api_router.include_router(instruction.router)      # 智能指令
api_router.include_router(conversation.router)     # 对话历史
