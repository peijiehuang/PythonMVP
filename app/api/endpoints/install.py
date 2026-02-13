from fastapi import APIRouter, HTTPException, Form
from fastapi.responses import JSONResponse
import os
import secrets
import logging
from app.core.config import settings
from app.core.database import engine
from app.core.security import ensure_admin_user
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

router = APIRouter()
logger = logging.getLogger(__name__)

# 延迟导入避免循环引用的标记回调
_mark_installed_callback = None

def set_mark_installed_callback(callback):
    global _mark_installed_callback
    _mark_installed_callback = callback

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

        # 4. 同步数据库结构（非破坏性：仅创建缺失的表，不删除数据）
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        # 5. 管理员账号处理 (创建或重置)
        async with AsyncSession(engine) as session:
            msg = await ensure_admin_user(session, admin_user, admin_pwd)

        # 6. 文件写入成功后再更新内存中的配置对象
        settings.PROJECT_NAME = project_name
        settings.SECRET_KEY = random_secret
        settings.FIRST_SUPERUSER = admin_user
        settings.FIRST_SUPERUSER_PASSWORD = admin_pwd

        logger.info(f"系统配置已重置/初始化。管理员: {admin_user}")
        # 更新内存安装标志，后续请求不再检测文件系统
        if _mark_installed_callback:
            _mark_installed_callback()
        return {"success": True, "message": f"安装成功！{msg}"}
        
    except Exception as e:
        if os.path.exists(".env"):
            os.remove(".env")
        logger.error(f"安装失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="安装失败，请检查日志获取详细信息")
