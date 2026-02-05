from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlmodel import Session, select

from .config import engine, logger
from .models import User
from .auth import get_password_hash

# 创建数据库表
def create_db_and_tables():
    from sqlmodel import SQLModel
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_type = engine.dialect.name
    logger.info(f"🔄 系统启动中... 数据库类型: {db_type}")
    create_db_and_tables()
    
    # 初始化默认管理员用户
    with Session(engine) as session:
        user = session.exec(select(User).where(User.username == "admin")).first()
        if not user:
            logger.info("⚡ 创建默认管理员用户: admin / admin")
            hashed_pwd = get_password_hash("admin")
            admin_user = User(username="admin", hashed_password=hashed_pwd)
            session.add(admin_user)
            session.commit()
    
    logger.info("✅ 数据库连接成功！")
    yield
    logger.info("🛑 系统正在关闭...")