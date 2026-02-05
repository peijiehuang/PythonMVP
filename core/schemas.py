from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 用户相关模式
class UserRead(BaseModel):
    id: int
    username: str
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# 物品相关模式
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class ItemCreate(ItemBase):
    pass

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ItemRead(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime