# Python MVP (FastAPI + SQLModel)

这是一个基于 **FastAPI** 和 **SQLModel** 构建的现代化 Python Web 架构。它采用清晰的层级设计，集成了 JWT 鉴权、自动数据库管理和 TDD 测试流程，旨在作为生产级 MVP 的标准模板。

---

## 📖 核心开发教程：如何添加新功能 (Control/Router)

在本架构中，添加一个新功能（例如“笔记 Note”模块）通常遵循以下 **4 个标准步骤**：

### Step 1: 在 `models/models.py` 定义模型
我们使用 SQLModel 的继承特性来复用字段，同时隔离“数据库表”和“API 接口数据结构”。

```python
# --- 笔记 (Note) 模型示例 ---
class NoteBase(SQLModel):
    title: str = Field(index=True, max_length=100)
    content: str
    is_public: bool = Field(default=False)

# 1. 数据库表 (Table) - 对应数据库真实结构
class Note(NoteBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")

# 2. 创建请求 (Request Body) - 用于 POST 请求验证
class NoteCreate(NoteBase):
    pass

# 3. 返回响应 (Response Body) - 用于 API 输出过滤敏感字段
class NoteRead(NoteBase):
    id: int
    owner_id: int
```

### Step 2: 在 `routers/` 创建控制器
新建 `routers/notes.py`。在这里处理业务逻辑、权限检查和数据库操作。

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from core.database import get_session
from core.security import get_current_user
from models.models import Note, NoteCreate, NoteRead, User

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
```

### Step 3: 在 `main.py` 注册路由
让 FastAPI 应用识别并启用你编写的控制器。

```python
# main.py
from routers import auth, items, notes # 1. 导入

# ...
app.include_router(auth.router)
app.include_router(items.router)
app.include_router(notes.router)      # 2. 挂载
```

### Step 4: 编写测试验证 (TDD)
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
- **前端演示**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

### 3. 执行测试

```powershell
pytest -v
```

---

## 📂 项目结构说明

```text
├── main.py             # 入口文件：组装路由、生命周期钩子
├── .env                # 环境配置文件 (敏感信息)
├── core/               # 核心配置层
│   ├── config.py       # Pydantic Settings 配置读取
│   ├── database.py     # Session 引擎与 get_session 注入函数
│   └── security.py     # JWT、密码 Hash、当前用户获取逻辑
├── models/             # 数据模型层
│   └── models.py       # SQLModel (Table & Schema)
├── routers/            # 控制器层 (Business Logic)
│   ├── auth.py         # 认证路由 (Login/Token)
│   └── items.py        # 业务逻辑 CRUD 示例 (含分页、搜索)
├── static/             # 静态资源 (前后端分离的前端代码)
└── test_main.py        # 自动化测试套件 (Pytest)
```

## 🤝 开发建议

1. **复杂查询**：推荐使用 `sqlmodel.select` 配合 `col(Model.field).contains()` 等高级语法。
2. **异步支持**：虽然本项目目前使用同步 Session，但 FastAPI 原生支持 `async def`。如果 IO 密集型操作较多，可考虑迁移至 `ext.asyncio`。
3. **安全性**：**SECRET_KEY** 严禁提交至 Git 仓库。
