from pydantic import BaseModel
from typing import Optional
from datetime import datetime

"""
数据传输对象定义 (Pydantic Schemas)
用于请求参数校验、API 响应字段过滤以及类型声明。
"""

# --- 用户认证相关 ---

class UserRead(BaseModel):
    """API 返回的用户信息（不包含密码）"""
    id: int
    username: str
    is_active: bool

class Token(BaseModel):
    """登录成功后返回的令牌格式"""
    access_token: str
    token_type: str

class TokenData(BaseModel):
    """从 JWT 载荷中提取的数据"""
    username: Optional[str] = None

# --- 业务物品相关 ---

class ItemBase(BaseModel):
    """物品基础字段"""
    name: str
    description: Optional[str] = None
    is_active: bool = True

class ItemCreate(ItemBase):
    """创建物品时的输入协议"""
    pass

class ItemUpdate(BaseModel):
    """更新物品时的输入协议（所有字段可选）"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ItemRead(ItemBase):
    """读取物品时的输出协议"""
    id: int
    created_at: datetime
    updated_at: datetime