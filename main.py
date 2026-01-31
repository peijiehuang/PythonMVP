import uvicorn
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Depends, Query, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlmodel import SQLModel, Field, Session, select, create_engine, col
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Security imports
from passlib.context import CryptContext
from jose import JWTError, jwt
from pydantic import BaseModel

# ==========================================
# 1. 基础设施配置 & 安全配置
# ==========================================
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///database.db")
SECRET_KEY = os.getenv("SECRET_KEY", "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, connect_args=connect_args, echo=False)

# 密码哈希工具
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 方案 (Token URL 指向登录接口)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ==========================================
# 2. 数据模型 (Models & Schemas)
# ==========================================

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

# ==========================================
# 3. 鉴权辅助函数
# ==========================================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_session():
    with Session(engine) as session:
        yield session

async def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = session.exec(select(User).where(User.username == token_data.username)).first()
    if user is None:
        raise credentials_exception
    return user

# ==========================================
# 4. 生命周期管理 (创建默认用户)
# ==========================================
def create_db_and_tables():
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

# ==========================================
# 5. 路由模块
# ==========================================
app = FastAPI(title="Universal MVP API (Auth)", version="3.2.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 鉴权路由 ---
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=UserRead)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# --- 业务路由 (保护写操作) ---
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
    # 公开读取接口，无需 Depends(get_current_user)
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

app.include_router(router)

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
