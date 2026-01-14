import uvicorn
import logging
import os
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from sqlmodel import SQLModel, Field, Session, select, create_engine, col
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# ==========================================
# 1. 基础设施配置
# ==========================================
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")

connect_args = {}
# 优化：使用 startswith 更加严谨，防止密码中包含 sqlite 字符误判
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

# ==========================================
# 2. 增强版数据模型 (MVVM/DTO 模式)
# ==========================================

# 2.1 基础模型 (包含共享字段)
class ItemBase(SQLModel):
    name: str = Field(index=True, max_length=255, schema_extra={"example": "Apple Stock"})
    description: Optional[str] = Field(default=None, schema_extra={"example": "Tech Giant"})
    is_active: bool = Field(default=True)

# 2.2 数据库表模型 (Entity) - 增加主键和时间
class Item(ItemBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 使用 UTC 时间，保证跨时区一致性
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# 2.3 创建模型 (DTO) - 剔除 id, created_at 等由后端生成的字段
class ItemCreate(ItemBase):
    pass

# 2.4 更新模型 (DTO) - 所有字段变为可选，允许只更新部分
class ItemUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

# 2.5 读取模型 (ViewModel) - 返回给前端的完整结构
class ItemRead(ItemBase):
    id: int
    created_at: datetime
    updated_at: datetime

# ==========================================
# 3. 生命周期与依赖注入
# ==========================================
def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    db_type = engine.dialect.name
    logger.info(f"🔄 系统启动中... 数据库类型: {db_type}")
    create_db_and_tables()
    logger.info("✅ 数据库连接成功！")
    yield
    logger.info("🛑 系统正在关闭...")

def get_session():
    with Session(engine) as session:
        yield session

# ==========================================
# 4. 路由模块
# ==========================================
router = APIRouter(prefix="/items", tags=["Items"])

# ⚠️ 注意：response_model 使用 ItemRead，输入使用 ItemCreate
@router.post("/", response_model=ItemRead, summary="创建新物品")
def create_item(item_in: ItemCreate, session: Session = Depends(get_session)):
    # 将 ItemCreate 转换为 Item 实体
    db_item = Item.model_validate(item_in)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@router.get("/", response_model=List[ItemRead], summary="查询物品列表")
def read_items(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    offset: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session)
):
    query = select(Item)
    if keyword:
        query = query.where(col(Item.name).contains(keyword))
    # 倒序排列
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
def update_item(item_id: int, item_in: ItemUpdate, session: Session = Depends(get_session)):
    db_item = session.get(Item, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # exclude_unset=True 非常关键，只更新前端传过来的字段
    input_data = item_in.model_dump(exclude_unset=True)
    
    for key, value in input_data.items():
        setattr(db_item, key, value)
    
    # 手动更新时间
    db_item.updated_at = datetime.now(timezone.utc)
    
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item

@router.delete("/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}

# ==========================================
# 5. App 配置与异常处理
# ==========================================
app = FastAPI(
    title="Universal MVP API",
    version="3.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 优化：全局异常捕获，防止吞掉 404 等常规 HTTP 错误
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # 如果已经是 HTTPException (如 404), 直接抛出，不当做 500 处理
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    
    logger.error(f"❌ 全局未捕获异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error", "detail": str(exc)},
    )

app.include_router(router)

@app.get("/", tags=["Home"])
def root():
    return {
        "message": "System Ready", 
        "time_utc": datetime.now(timezone.utc),
        "db_driver": engine.dialect.name
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)