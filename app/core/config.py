from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    """应用全局配置类"""
    PROJECT_NAME: str = "Cosmic MVP API"
    VERSION: str = "3.3.0"
    API_V1_STR: str = "/api/v1"
    
    # 安全与加密
    # 生产环境务必修改此密钥
    SECRET_KEY: str = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # 初始管理员配置
    FIRST_SUPERUSER: str = "admin"
    FIRST_SUPERUSER_PASSWORD: str = "admin"
    
    # 数据库配置
    DATABASE_URL: str = "sqlite:///database.db"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    @property
    def ASYNC_DATABASE_URL(self) -> str:
        """根据 DATABASE_URL 自动生成异步驱动协议链接"""
        if self.DATABASE_URL.startswith("sqlite"):
            return self.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://")
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

    # Pydantic Settings 配置：支持读取 .env 文件
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_ignore_empty=True,
        extra="ignore"
    )

settings = Settings()
