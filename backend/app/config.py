from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "FilesReadSystem"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # 数据库
    MONGODB_URL: str
    MONGODB_DB_NAME: str
    REDIS_URL: str
    
    # AI 相关
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL_NAME: str
    
    # 文件路径
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    UPLOAD_DIR: str = "data/uploads"
    
    # 允许 Pydantic 从 .env 文件读取
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env", 
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()