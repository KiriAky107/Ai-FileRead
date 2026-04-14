"""
FastAPI 应用主入口
"""
# ========== 压制 MongoDB 疯狂刷屏日志 ==========
import logging
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("pymongo.topology").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
# ==============================================

import logging
import logging.handlers
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Callable
from functools import wraps

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.api import api_router
from app.core.database import mysql_db, mongodb, redis_db

# ==================== 日志配置 ====================

def setup_logging():
    """配置应用日志系统"""
    import os
    from pathlib import Path

    # 根日志配置
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # 日志目录
    log_dir = Path("data/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 日志文件路径
    log_file = log_dir / "app.log"
    error_log_file = log_dir / "error.log"

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(console_formatter)

    # 文件处理器 (所有日志)
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(funcName)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)

    # 错误日志处理器 (仅ERROR及以上)
    error_file_handler = logging.handlers.RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding="utf-8"
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(file_formatter)

    # 根日志器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers = []
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_file_handler)

    # 第三方库日志级别
    for lib in ["uvicorn", "uvicorn.access", "fastapi", "httpx", "sqlalchemy"]:
        logging.getLogger(lib).setLevel(logging.WARNING)

    root_logger.info(f"日志系统初始化完成 | 日志目录: {log_dir}")
    root_logger.info(f"主日志文件: {log_file} | 错误日志: {error_log_file}")

    return root_logger

# 初始化日志
setup_logging()
logger = logging.getLogger(__name__)


# ==================== 请求日志中间件 ====================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 记录每个请求的详细信息"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # 记录请求
        logger.info(f"→ [{request_id}] {request.method} {request.url.path}")

        try:
            response = await call_next(request)

            # 记录响应
            logger.info(
                f"← [{request_id}] {request.method} {request.url.path} "
                f"| 状态: {response.status_code} | 耗时: N/A"
            )

            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            logger.error(f"✗ [{request_id}] {request.method} {request.url.path} | 异常: {str(e)}")
            raise


# ==================== 请求追踪装饰器 ====================

def log_async_function(func: Callable) -> Callable:
    """异步函数日志装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        func_name = func.__name__
        logger.debug(f"→ {func_name} 开始执行")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"← {func_name} 执行完成")
            return result
        except Exception as e:
            logger.error(f"✗ {func_name} 执行失败: {str(e)}")
            raise
    return wrapper


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理

    启动时: 初始化数据库连接
    关闭时: 关闭数据库连接
    """
    # 启动时
    logger.info("正在初始化数据库连接...")

    # 初始化 MySQL
    try:
        await mysql_db.init_db()
        logger.info("✓ MySQL 初始化成功")
    except Exception as e:
        logger.error(f"✗ MySQL 初始化失败: {e}")

    # 初始化 MongoDB
    try:
        await mongodb.connect()
        await mongodb.create_indexes()
        logger.info("✓ MongoDB 初始化成功")
    except Exception as e:
        logger.error(f"✗ MongoDB 初始化失败: {e}")

    # 初始化 Redis
    try:
        await redis_db.connect()
        logger.info("✓ Redis 初始化成功")
    except Exception as e:
        logger.error(f"✗ Redis 初始化失败: {e}")

    logger.info("数据库初始化完成")
    yield

    # 关闭时
    logger.info("正在关闭数据库连接...")
    await mysql_db.close()
    await mongodb.close()
    await redis_db.close()
    logger.info("数据库连接已关闭")


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.APP_NAME,
    description="基于大语言模型的文档理解与多源数据融合系统",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,  # 添加生命周期管理
)

# 配置 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加请求日志中间件
app.add_middleware(RequestLoggingMiddleware)

# 注册 API 路由
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "status": "online",
        "version": "1.0.0",
        "debug_mode": settings.DEBUG,
        "api_docs": f"{settings.API_V1_STR}/docs"
    }


@app.get("/health")
async def health_check():
    """
    健康检查接口

    返回各数据库连接状态
    """
    # 检查各数据库连接状态
    mysql_status = "connected" if mysql_db.async_engine else "disconnected"
    mongodb_status = "connected" if mongodb.client else "disconnected"
    redis_status = "connected" if redis_db.is_connected else "disconnected"

    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "databases": {
            "mysql": mysql_status,
            "mongodb": mongodb_status,
            "redis": redis_status,
        }
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=settings.DEBUG
    )
