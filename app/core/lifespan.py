from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.config import settings
from app.core.database import engine
from app.core.security import get_password_hash
from app.models.models import User

logger = logging.getLogger(__name__)

async def create_db_and_tables():
    """执行 SQLModel 元数据建表"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用全生命周期管理"""
    # [1. 启动阶段]
    # 开发模式下：自动检测并创建表
    await create_db_and_tables()
    
    # 初始化默认管理员
    async with AsyncSession(engine) as session:
        result = await session.execute(select(User).where(User.username == settings.FIRST_SUPERUSER))
        user = result.scalars().first()
        if not user:
            logger.info(f"⚡ 正在初始化默认管理员用户: {settings.FIRST_SUPERUSER} / ******")
            hashed_pwd = get_password_hash(settings.FIRST_SUPERUSER_PASSWORD)
            admin_user = User(username=settings.FIRST_SUPERUSER, hashed_password=hashed_pwd)
            session.add(admin_user)
            await session.commit()
    
    logger.info("✅ 异步数据库连接已就绪")
    
    yield # --- 程序运行中 ---
    
    # [2. 关闭阶段]
    logger.info("🛑 正在关闭应用并释放资源...")
    # 必须显式关闭引擎连接池，否则进程可能卡死
    await engine.dispose()
    logger.info("👋 数据库连接已安全回收，安全退出")
