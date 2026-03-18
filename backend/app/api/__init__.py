"""
API 路由注册模块
"""
from fastapi import APIRouter
from app.api.endpoints import upload, ai_analyze, visualization, analysis_charts

# 创建主路由
api_router = APIRouter()

# 注册各模块路由
api_router.include_router(upload.router)
api_router.include_router(ai_analyze.router)
api_router.include_router(visualization.router)
api_router.include_router(analysis_charts.router)
