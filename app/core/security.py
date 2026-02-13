from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Union
from jose import jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.config import settings

# 密码加密上下文：强制使用 bcrypt 算法
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_access_token(subject: Union[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """生成 JWT 访问令牌"""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证原始密码与哈希值是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """将明文密码转化为加盐哈希值"""
    return pwd_context.hash(password)

async def ensure_admin_user(session: AsyncSession, username: str, password: str) -> str:
    """创建或重置管理员用户，返回操作描述"""
    from app.models.models import User
    result = await session.execute(select(User).where(User.username == username))
    existing_user = result.scalars().first()
    hashed_pwd = get_password_hash(password)

    if existing_user:
        existing_user.hashed_password = hashed_pwd
        session.add(existing_user)
        msg = f"已重置管理员 {username} 的密码"
    else:
        admin_user = User(username=username, hashed_password=hashed_pwd)
        session.add(admin_user)
        msg = f"已创建管理员账号 {username}"

    await session.commit()
    return msg