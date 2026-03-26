from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "FilesReadSystem"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # ==================== 数据库配置 ====================

    # MongoDB 配置 (非结构化数据存储)
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB_NAME: str = "document_system"

    # MySQL 配置 (结构化数据存储)
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DATABASE: str = "document_system"
    MYSQL_CHARSET: str = "utf8mb4"

    # Redis 配置 (缓存/任务队列)
    REDIS_URL: str = "redis://localhost:6379/0"

    # ==================== AI 相关配置 ====================
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.minimax.chat"
    LLM_MODEL_NAME: str = "MiniMax-Text-01"

    # ==================== 文件路径配置 ====================
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: str = "data/uploads"

    # ==================== RAG/向量数据库配置 ====================
    FAISS_INDEX_DIR: str = "data/faiss"

    # 允许 Pydantic 从 .env 文件读取
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

    @property
    def mysql_url(self) -> str:
        """生成MySQL连接URL"""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset={self.MYSQL_CHARSET}"
        )

settings = Settings()