# Python MVP (FastAPI + SQLModel)

这是一个基于 **FastAPI** 和 **SQLModel** 构建的现代化 Python Web 架构。它采用清晰的层级设计，集成了 JWT 鉴权、自动数据库管理和 TDD 测试流程，旨在作为生产级 MVP 的标准模板。

---

## 🎯 项目概览

本项目提供了一个完整的 Web 应用框架，包含以下核心功能：

- **用户认证系统**：基于 JWT 的用户登录、注册和权限管理
- **物品管理系统**：完整的 CRUD 操作，支持分页和搜索
- **自动数据库管理**：使用 SQLModel 自动创建数据库表结构
- **API 文档**：自动生成 Swagger UI 和 ReDoc 文档
- **测试框架**：集成 Pytest 测试套件，支持 TDD 开发流程

---

## 📖 核心开发教程：如何添加新功能 (Control/Router)

在本架构中，添加一个新功能（例如“笔记 Note”模块）通常遵循以下 **4 个标准步骤**：

### Step 1: 在 `core/models.py` 定义数据库模型
我们使用 SQLModel 定义数据库表结构。

```python
# --- 笔记 (Note) 模型示例 ---
class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, max_length=100)
    content: str
    is_public: bool = Field(default=False)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### Step 2: 在 `core/schemas.py` 定义数据验证模式
我们使用 Pydantic 定义 API 接口的数据结构。

```python
# --- 笔记 (Note) 模式示例 ---
class NoteBase(BaseModel):
    title: str
    content: str
    is_public: bool = False

class NoteCreate(NoteBase):
    pass

class NoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_public: Optional[bool] = None

class NoteRead(NoteBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
```

### Step 3: 在 `core/routes/` 创建控制器
新建 `core/routes/notes.py`。在这里处理业务逻辑、权限检查和数据库操作。

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import Optional, List
from datetime import datetime, timezone

from ..models import Note, User
from ..schemas import NoteCreate, NoteUpdate, NoteRead
from ..auth import get_session, get_current_user

router = APIRouter(prefix="/notes", tags=["Notes"])

@router.post("/", response_model=NoteRead)
def create_note(
    note_in: NoteCreate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 只有登录用户可访问
):
    db_note = Note.model_validate(note_in)
    db_note.owner_id = current_user.id
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    return db_note

@router.get("/", response_model=List[NoteRead])
def read_notes(
    offset: int = 0, 
    limit: int = 100, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 只有登录用户可访问
):
    query = select(Note).where(Note.owner_id == current_user.id)
    query = query.order_by(Note.created_at.desc())
    query = query.offset(offset).limit(limit)
    return session.exec(query).all()

@router.get("/{note_id}", response_model=NoteRead)
def read_note(
    note_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 只有登录用户可访问
):
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this note")
    return note

@router.patch("/{note_id}", response_model=NoteRead)
def update_note(
    note_id: int, 
    note_in: NoteUpdate, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 只有登录用户可访问
):
    db_note = session.get(Note, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    if db_note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this note")
    
    input_data = note_in.model_dump(exclude_unset=True)
    for key, value in input_data.items():
        setattr(db_note, key, value)
    db_note.updated_at = datetime.now(timezone.utc)
    
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    return db_note

@router.delete("/{note_id}")
def delete_note(
    note_id: int, 
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user) # 🔒 只有登录用户可访问
):
    note = session.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    if note.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this note")
    session.delete(note)
    session.commit()
    return {"ok": True}
```

### Step 4: 在 `core/routes/__init__.py` 导出路由
让 FastAPI 应用识别并启用你编写的控制器。

```python
# core/routes/__init__.py
from .auth import router as auth
from .items import router as items
from .notes import router as notes  # 添加新的路由
```

### Step 5: 编写测试验证 (TDD)
在 `test_main.py` 中添加测试用例，确保功能正常。

```python
def test_create_note(client, token_headers):
    response = client.post(
        "/notes/",
        headers=token_headers,
        json={"title": "Test Note", "content": "Hello World"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Note"
    assert data["content"] == "Hello World"

def test_read_notes(client, token_headers):
    # 先创建一个笔记
    create_response = client.post(
        "/notes/",
        headers=token_headers,
        json={"title": "Test Note", "content": "Hello World"}
    )
    assert create_response.status_code == 200
    
    # 然后读取所有笔记
    response = client.get("/notes/", headers=token_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
```

---

## ⚙️ 环境配置 (.env)

项目使用 `python-dotenv` 管理配置。在根目录下创建 `.env` 文件：

```env
# 数据库连接串 (默认使用 SQLite)
DATABASE_URL=sqlite:///database.db

# JWT 签名密钥 (生产环境请务必更换)
# 生成建议: openssl rand -hex 32
SECRET_KEY=your_super_secret_safe_key_here

# Token 过期时间 (分钟)
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## 🛠️ 技术栈与优势

- **SQLModel**: 结合 SQLAlchemy 的强大 ORM 和 Pydantic 的严谨验证，一份代码搞定所有。
- **依赖注入**: 利用 FastAPI 的 `Depends` 实现数据库 Session 和用户鉴权的解耦。
- **自动文档**: 自动生成 Swagger UI (`/docs`) 和 ReDoc (`/redoc`)。
- **安全加固**: 密码使用 `bcrypt` 强哈希存储，Token 采用 JWT 标准。
- **模块化设计**: 清晰的代码结构，易于维护和扩展。

---

## 🚀 快速开始

### 1. 环境准备 (Windows)

```powershell
# 创建并激活虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 安装依赖
pip install -r requirements.txt
```

### 2. 运行项目

```powershell
# 运行服务
python main.py
```
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **前端演示**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 3. 执行测试

```powershell
# 运行所有测试
pytest -v

# 运行特定测试文件
pytest test_main.py -v

# 运行特定测试函数
pytest test_main.py::test_create_item -v
```

---

## 📡 API 接口使用指南

### 1. 用户认证

#### 登录获取 Token

**请求**:
```http
POST /token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

#### 获取当前用户信息

**请求**:
```http
GET /users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应**:
```json
{
  "id": 1,
  "username": "admin",
  "is_active": true
}
```

### 2. 物品管理

#### 创建物品

**请求**:
```http
POST /items/
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "name": "Apple Stock",
  "description": "Tech Giant",
  "is_active": true
}
```

**响应**:
```json
{
  "id": 1,
  "name": "Apple Stock",
  "description": "Tech Giant",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 读取物品列表

**请求**:
```http
GET /items/?keyword=Apple&offset=0&limit=10
```

**响应**:
```json
[
  {
    "id": 1,
    "name": "Apple Stock",
    "description": "Tech Giant",
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### 读取单个物品

**请求**:
```http
GET /items/1
```

**响应**:
```json
{
  "id": 1,
  "name": "Apple Stock",
  "description": "Tech Giant",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 更新物品

**请求**:
```http
PATCH /items/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
Content-Type: application/json

{
  "description": "Updated description"
}
```

**响应**:
```json
{
  "id": 1,
  "name": "Apple Stock",
  "description": "Updated description",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### 删除物品

**请求**:
```http
DELETE /items/1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**响应**:
```json
{
  "ok": true
}
```

---

## 📂 项目结构说明

```text
├── main.py              # 主入口文件：组装路由、生命周期钩子
├── core/                # 核心模块目录
│   ├── __init__.py      # 包初始化文件
│   ├── config.py        # 配置模块：数据库连接、日志配置、密钥配置等
│   ├── models.py        # 数据库模型：定义数据库表结构
│   ├── schemas.py       # 数据验证模式：定义 API 接口数据结构
│   ├── auth.py          # 鉴权模块：密码哈希、JWT 令牌生成、获取当前用户等
│   ├── lifespan.py      # 生命周期管理：创建数据库表、初始化默认管理员用户等
│   └── routes/          # 路由模块目录
│       ├── __init__.py  # 路由包初始化文件
│       ├── auth.py      # 鉴权相关路由：登录、获取当前用户信息等
│       └── items.py     # 物品相关路由：创建、读取、更新、删除物品等
├── static/              # 静态资源目录
├── database.db          # SQLite 数据库文件
├── requirements.txt     # 项目依赖
├── test_main.py         # 自动化测试套件
└── README.md            # 项目说明文档
```

---

## 🚀 部署指南

### 1. 开发环境部署

按照「快速开始」部分的步骤进行操作即可。

### 2. 生产环境部署

#### 使用 Gunicorn + Uvicorn

```bash
# 安装依赖
pip install gunicorn uvicorn

# 启动服务
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

#### 使用 Docker

创建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

构建并运行 Docker 容器:

```bash
docker build -t python-mvp .
docker run -d -p 8000:8000 python-mvp
```

---

## 🧪 测试指南

### 1. 编写测试用例

在 `test_main.py` 文件中编写测试用例，遵循以下原则：

- **测试用例应该独立**：每个测试用例应该测试一个特定的功能点
- **测试用例应该可重复**：多次运行测试应该得到相同的结果
- **测试用例应该覆盖边界情况**：测试各种可能的输入和场景

### 2. 运行测试

```powershell
# 运行所有测试
pytest -v

# 运行特定测试文件
pytest test_main.py -v

# 运行特定测试函数
pytest test_main.py::test_create_item -v

# 生成测试覆盖率报告
pytest --cov=core test_main.py
```

### 3. 测试最佳实践

- **使用 fixtures**：使用 Pytest 的 fixtures 来设置和清理测试环境
- **模拟外部依赖**：对于外部依赖（如数据库、API 调用），使用模拟对象
- **测试异常情况**：确保测试覆盖了各种异常情况
- **测试性能**：对于关键功能，添加性能测试

---

## ❓ 常见问题及解决方案

### 1. 数据库连接失败

**问题**：无法连接到数据库
**解决方案**：
- 检查 `DATABASE_URL` 配置是否正确
- 确保数据库服务正在运行
- 对于 SQLite，确保目录有写入权限

### 2. JWT 令牌验证失败

**问题**：无法验证 JWT 令牌
**解决方案**：
- 检查 `SECRET_KEY` 是否与生成令牌时使用的密钥一致
- 确保令牌没有过期
- 检查令牌格式是否正确

### 3. 测试失败

**问题**：测试用例失败
**解决方案**：
- 检查测试用例是否正确
- 检查业务逻辑是否符合预期
- 查看测试日志，了解具体失败原因

### 4. 部署问题

**问题**：部署后服务无法访问
**解决方案**：
- 检查端口是否正确配置
- 检查防火墙设置
- 查看服务日志，了解具体错误原因

---

## 🤝 开发建议

1. **复杂查询**：推荐使用 `sqlmodel.select` 配合 `col(Model.field).contains()` 等高级语法。
2. **异步支持**：虽然本项目目前使用同步 Session，但 FastAPI 原生支持 `async def`。如果 IO 密集型操作较多，可考虑迁移至 `ext.asyncio`。
3. **安全性**：**SECRET_KEY** 严禁提交至 Git 仓库。
4. **模块化设计**：遵循项目的模块化设计原则，将代码按照功能拆分为不同的模块，保持代码的清晰和可维护性。
5. **代码质量**：使用 Pylint 或 Flake8 等工具检查代码质量，使用 Black 或 isort 等工具格式化代码。
6. **文档**：为关键函数和模块添加文档字符串，保持代码的可读性。
7. **版本控制**：使用 Git 进行版本控制，遵循 Git 最佳实践，如使用语义化版本号、编写清晰的提交信息等。

---

## 📚 资源链接

- **FastAPI 官方文档**：[https://fastapi.tiangolo.com/](https://fastapi.tiangolo.com/)
- **SQLModel 官方文档**：[https://sqlmodel.tiangolo.com/](https://sqlmodel.tiangolo.com/)
- **Pydantic 官方文档**：[https://docs.pydantic.dev/](https://docs.pydantic.dev/)
- **SQLAlchemy 官方文档**：[https://docs.sqlalchemy.org/](https://docs.sqlalchemy.org/)
- **JWT 官方文档**：[https://jwt.io/](https://jwt.io/)
- **Pytest 官方文档**：[https://docs.pytest.org/](https://docs.pytest.org/)

---

## 🎉 项目启动

项目已经成功配置并启动，您可以通过以下方式访问：

- **Swagger UI**：[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**：[http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **前端演示**：[http://127.0.0.1:8000/](http://127.0.0.1:8000/)

默认管理员账号：
- **用户名**：admin
- **密码**：admin

祝您开发愉快！
