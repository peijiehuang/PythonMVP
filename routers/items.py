from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, col

from core.database import get_session
from core.security import get_current_user
from models.models import User, Item, ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["Items"])

@router.post("/", response_model=ItemRead)
def create_item(
    item_in: ItemCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 Protected
):
    db_item = Item.model_validate(item_in)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@router.get("/", response_model=List[ItemRead])
def read_items(
    keyword: Optional[str] = Query(None),
    offset: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session)
):
    query = select(Item)
    if keyword:
        query = query.where(col(Item.name).contains(keyword))
    query = query.order_by(Item.created_at.desc())
    query = query.offset(offset).limit(limit)
    return session.exec(query).all()

@router.get("/{item_id}", response_model=ItemRead)
def read_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@router.patch("/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int, 
    item_in: ItemUpdate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 Protected
):
    db_item = session.get(Item, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    input_data = item_in.model_dump(exclude_unset=True)
    for key, value in input_data.items():
        setattr(db_item, key, value)
    db_item.updated_at = datetime.now(timezone.utc)
    
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_item(
    item_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 Protected
):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
