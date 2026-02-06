from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import select, SQLModel
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import os

from app.core.config import settings
from app.core.database import engine
from app.core.security import get_password_hash
from app.models.models import User
from app.core.scheduler import start_scheduler, shutdown_scheduler, sync_scheduler_with_db

logger = logging.getLogger(__name__)

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # [1. 启动阶段]
    # 如果已经安装了配置文件，则尝试初始化
    if os.path.exists(".env"):
        await create_db_and_tables()
        
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
        
        # 启动后台定时任务
        start_scheduler()
        await sync_scheduler_with_db()
    else:
        logger.warning("⚠️ 检测到系统尚未初始化，请访问 /install 进行安装")
    
    yield # --- 程序运行中 ---
    
    # [2. 关闭阶段]
    if os.path.exists(".env"):
        logger.info("🛑 正在关闭应用并释放资源...")
        # 关闭定时任务
        shutdown_scheduler()
        await engine.dispose()
        logger.info("👋 资源已回收")