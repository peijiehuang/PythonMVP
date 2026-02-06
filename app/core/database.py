from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from app.core.config import settings

# 针对 SQLite 的特殊连接参数
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

# 创建全异步数据库引擎
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL, 
    echo=False, 
    future=True, 
    connect_args=connect_args
)

# 异步 Session 工厂：expire_on_commit=False 避免对象在提交后失效
async_session_maker = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖注入：获取异步数据库会话"""
    async with async_session_maker() as session:
        yield session

async def create_db_and_tables():
    """手动创建数据库表（通常用于开发环境）"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
