from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field
from pydantic import BaseModel

# --- 用户相关 ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    hashed_password: str
    is_active: bool = Field(default=True)

class UserRead(BaseModel):
    id: int
    username: str
    is_active: bool

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# --- 物品相关 ---
class ItemBase(SQLModel):
    name: str = Field(index=True, max_length=255, schema_extra={"example": "Apple Stock"})
    description: Optional[str] = Field(default=None, schema_extra={"example": "Tech Giant"})
    is_active: bool = Field(default=True)

class Item(ItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ItemCreate(ItemBase):
    pass

class ItemUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ItemRead(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime
