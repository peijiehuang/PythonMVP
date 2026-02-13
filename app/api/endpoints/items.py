from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Query, HTTPException
from sqlmodel import select, col

from app.api.deps import SessionDep, CurrentUser
from app.models.models import Item
from app.schemas.schemas import ItemCreate, ItemUpdate, ItemRead
from app.schemas.responses import resp_ok

router = APIRouter()

@router.post("/", response_model=None)
async def create_item(
    item_in: ItemCreate, 
    session: SessionDep,
    current_user: CurrentUser # 🔒 需要登录
):
    """创建新物品"""
    db_item = Item.model_validate(item_in)
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return resp_ok(data=db_item)

@router.get("/", response_model=None)
async def read_items(
    session: SessionDep,
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """分页获取物品列表（公开接口）"""
    query = select(Item)
    if keyword:
        query = query.where(col(Item.name).contains(keyword))
    query = query.order_by(Item.created_at.desc())
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    return resp_ok(data=result.scalars().all())

@router.get("/{item_id}", response_model=None)
async def read_item(item_id: int, session: SessionDep):
    """获取单个物品详情"""
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    return resp_ok(data=item)

@router.patch("/{item_id}", response_model=None)
async def update_item(
    item_id: int, 
    item_in: ItemUpdate, 
    session: SessionDep,
    current_user: CurrentUser # 🔒 需要登录
):
    """部分更新物品信息"""
    db_item = await session.get(Item, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="物品不存在")
    
    # 提取非空输入数据进行合并
    input_data = item_in.model_dump(exclude_unset=True)
    for key, value in input_data.items():
        setattr(db_item, key, value)
    db_item.updated_at = datetime.now(timezone.utc)
    
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return resp_ok(data=db_item)

@router.delete("/{item_id}")
async def delete_item(
    item_id: int, 
    session: SessionDep,
    current_user: CurrentUser # 🔒 需要登录
):
    """物理删除指定物品"""
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="物品不存在")
    await session.delete(item)
    await session.commit()
    return resp_ok(message="物品删除成功")
