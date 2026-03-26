"""
FastAPI 应用主入口
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import api_router
from app.core.database import mysql_db, mongodb, redis_db

# 配置日志
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


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
