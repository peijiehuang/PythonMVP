from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
import os
import secrets
import logging
from app.core.config import settings
from app.core.database import engine
from app.core.security import get_password_hash
from app.models.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, SQLModel

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/check")
async def check_status():
    """检测是否已安装"""
    return {"installed": os.path.exists(".env")}

@router.post("/setup")
async def perform_install(
    project_name: str = Form(...),
    admin_user: str = Form(...),
    admin_pwd: str = Form(...)
):
    """执行安装/重置配置：保留数据，仅同步结构并重置管理员"""
    if os.path.exists(".env"):
        raise HTTPException(status_code=400, detail="系统已安装，请勿重复操作")

    # 1. 生成新的安全密钥
    random_secret = secrets.token_hex(32)
    
    # 2. 准备配置文件内容
    env_content = f"""# Cosmic MVP 自动生成配置
PROJECT_NAME="{project_name}"
VERSION=1.0.0

# 数据库配置
DATABASE_URL=sqlite:///database.db

# 安全配置
SECRET_KEY={random_secret}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# 初始管理员凭据
FIRST_SUPERUSER={admin_user}
FIRST_SUPERUSER_PASSWORD={admin_pwd}

# 日志级别
LOG_LEVEL=INFO
"""
    
    try:
        # 3. 写入 .env 文件
        with open(".env", "w", encoding="utf-8") as f:
            f.write(env_content)
        
        # 4. 同步更新内存中的配置对象
        settings.PROJECT_NAME = project_name
        settings.SECRET_KEY = random_secret
        settings.FIRST_SUPERUSER = admin_user
        settings.FIRST_SUPERUSER_PASSWORD = admin_pwd
        
        # 5. 同步数据库结构（非破坏性：仅创建缺失的表，不删除数据）
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        
        # 6. 管理员账号处理 (创建或重置)
        async with AsyncSession(engine) as session:
            # 查询是否存在该用户
            result = await session.execute(select(User).where(User.username == admin_user))
            existing_user = result.scalars().first()
            hashed_pwd = get_password_hash(admin_pwd)
            
            if existing_user:
                # 存在则更新密码（视为找回管理员权限）
                existing_user.hashed_password = hashed_pwd
                session.add(existing_user)
                msg = f"配置同步成功，已重置管理员 {admin_user} 的密码。"
            else:
                # 不存在则新建
                admin_user_obj = User(username=admin_user, hashed_password=hashed_pwd)
                session.add(admin_user_obj)
                msg = f"安装成功！已创建管理员账号 {admin_user}。"
            
            await session.commit()
            
        logger.info(f"✨ 系统配置已重置/初始化。管理员: {admin_user}")
        return {"success": True, "message": msg}
        
    except Exception as e:
        if os.path.exists(".env"):
            os.remove(".env")
        logger.error(f"安装失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"安装失败: {str(e)}")
