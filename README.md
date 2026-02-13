# Cosmic MVP - 全栈极速开发框架 (v4.0)

**Cosmic MVP** 是一个专为"想快速把想法变成产品"的开发者设计的全栈脚手架。
它不仅是一个后端框架，更是一套**完整的生产力方案**：自带安装向导、自带后台任务监控、自带代码生成器、自带漂亮的 UI 界面。

### 核心亮点

- **开箱即用** — 安装向导自动初始化数据库、管理员账号、密钥，零配置启动
- **代码生成器** — 选中数据库表，一键生成 CRUD 后端接口 + Schema + 前端页面，自动注册路由
- **后台任务引擎** — 定时任务即插即用，网页端实时查看日志、调整执行频率
- **前后端一体** — Vue 3 + DaisyUI 精美界面，无需分离部署
- **全异步架构** — FastAPI + SQLModel + AsyncIO，天然高性能

---

## 快速索引

| 我想... | 去哪看 |
|---------|--------|
| 第一次用，快速跑起来 | [3分钟快速上手](#3分钟快速上手) |
| 用代码生成器一键出代码 | [代码生成器](#代码生成器一键生成crud) |
| 手动写一个新功能 | [开发新功能教程](#怎么开发一个新功能保姆级教程) |
| 加一个定时任务 | [后台定时任务](#怎么写后台定时任务) |
| 看有哪些 API | [API 概览](#api-概览) |
| 避免踩坑 | [小白避坑指南](#小白避坑指南必看) |

---

## 小白避坑指南（必看！）

在开发过程中，请务必记住以下几点，能帮你节省 80% 的排错时间：

1.  **Python 的"等一等" (`await`)**：
    本项目是异步框架。只要你操作数据库（例如 `session.add`, `session.commit`），前面**必须**写 `await`。
    - 错误：`session.commit()`
    - 正确：`await session.commit()`

2.  **修改模型后要"同步"数据库**：
    如果你在 `models.py` 里增加了一个字段或一个新表，数据库并不会自动感知。
    你**必须**在命令行运行：`python run.py mig`，然后按提示输入一个名字。

3.  **注意缩进！**
    Python 对缩进非常敏感。如果报错 `IndentationError`，请检查你的代码行首是否有乱入的空格。

4.  **管理员登录**：
    默认账号/密码是 `admin` / `admin`。如果你忘了，删除文件夹里的 `.env` 文件重新刷新页面即可重设。

---

## 3分钟快速上手

### 1. 准备环境
```bash
# 1. 创建虚拟环境 (像在电脑里建一个独立小黑屋，防止库冲突)
python -m venv .venv

# 2. 激活它
.\.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Mac/Linux

# 3. 安装工具包
pip install -r requirements.txt
```

### 2. 启动并安装
```bash
python run.py dev
```
启动后访问：[http://localhost:8000](http://localhost:8000)
系统会自动引导你进入安装向导，设置管理员账号，完成后即可使用。

### 3. Docker 部署（可选）
```bash
docker-compose up -d
```

---

## 代码生成器（一键生成CRUD）

Cosmic MVP 内置代码生成器，选中数据库表即可自动生成完整的 CRUD 代码（后端接口 + Schema + 前端页面），**让你从定义模型到拥有完整功能页面只需 3 步**。

### 完整示例：开发一个"商品管理"功能

**第一步：定义模型** (`app/models/models.py`)
```python
class Product(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255)
    price: float = Field(default=0)
    description: Optional[str] = Field(default=None)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

**第二步：同步数据库**
```bash
python run.py mig
```

**第三步：打开代码生成器**

访问 [http://localhost:8000/codegen](http://localhost:8000/codegen)，选中 `Product` 表，点击 **Save to Project**，重启服务。

完成！你现在拥有了：

| 自动生成的文件 | 路径 | 包含内容 |
|---------------|------|---------|
| 后端接口 | `app/api/endpoints/products.py` | POST 创建、GET 列表(搜索+分页)、GET 详情、PATCH 更新、DELETE 删除 |
| 数据校验 | `app/schemas/schemas_products.py` | ProductCreate / ProductUpdate / ProductRead 三个 DTO |
| 前端页面 | `static/products.html` | Vue 3 + DaisyUI 完整 CRUD 页面（含登录、搜索、创建/编辑弹窗） |

同时自动完成：
- 在 `app/api/api.py` 注册 `/products` 路由
- 在 `main.py` 添加 `/products` 页面路由

> **安全机制**：已存在的文件不会被覆盖，你也可以先下载代码到本地检查后再手动放入项目。

### 代码生成器支持的字段类型映射

| SQLAlchemy 类型 | 生成的 Python 类型 | 前端表单控件 |
|----------------|-------------------|-------------|
| INTEGER / BIGINTEGER | `int` | `<input type="number">` |
| VARCHAR / TEXT | `str` | `<input type="text">` 或 `<textarea>`（可空字段） |
| BOOLEAN | `bool` | `<toggle>` 开关 |
| FLOAT / NUMERIC | `float` | `<input type="number">` |
| DATETIME | `datetime` | 自动管理（created_at / updated_at） |

---

## 怎么开发一个新功能？(保姆级教程)

> **推荐**：如果你的功能是标准 CRUD（增删改查），直接使用[代码生成器](#代码生成器一键生成crud)会更快。以下教程适合需要自定义逻辑的场景。

假设你想做一个"笔记记录"功能：

### 第一步：画好笔记的样子 (`app/models/models.py`)
```python
class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(description="笔记标题")
    content: str = Field(description="内容")
```

### 第二步：告诉数据库 (`python run.py mig`)
在命令行输入这行命令，它是全自动的。

### 第三步：写接口逻辑 (`app/api/endpoints/notes.py`)
```python
from app.api.deps import SessionDep, CurrentUser
from app.schemas.responses import resp_ok

@router.post("/add")
async def add_note(title: str, content: str, session: SessionDep):
    new_note = Note(title=title, content=content)
    session.add(new_note)
    await session.commit() # 别忘了 await!
    return resp_ok(data=new_note, message="笔记保存成功")
```

### 第四步：注册路由 (`app/api/api.py`)
```python
from app.api.endpoints import notes
api_router.include_router(notes.router, prefix="/notes", tags=["notes"])
```

---

## 怎么写后台定时任务？

Cosmic MVP 的后台任务是"即插即用"的：

1.  在 `app/tasks/` 下新建个 `my_job.py`。
2.  粘贴以下代码：
```python
from app.core.scheduler import register_task, task_print

@register_task("自动清理垃圾记录")
async def my_clean_task():
    task_print("清理任务启动中...") # 这里的文字会实时显示在网页上
    # 在这里写你的清理代码
    task_print("清理完毕！")
```
3.  打开浏览器访问 [http://localhost:8000/static/tasks.html](http://localhost:8000/static/tasks.html)。
    你会发现"自动清理垃圾记录"已经出现在列表里了，你可以随便改它的执行频率。

---

## 页面导航

| 页面 | 地址 | 说明 |
|------|------|------|
| 主仪表盘 | [/](http://localhost:8000/) | 物品管理示例（CRUD 演示） |
| 代码生成器 | [/codegen](http://localhost:8000/codegen) | 选表生成代码、预览、下载、一键保存 |
| 任务监控 | [/static/tasks.html](http://localhost:8000/static/tasks.html) | 后台任务列表、日志、手动触发 |
| 安装向导 | [/install](http://localhost:8000/install) | 首次启动时自动跳转，设置管理员和密钥 |
| Swagger 文档 | [/docs](http://localhost:8000/docs) | FastAPI 自动生成的交互式 API 文档 |

---

## 项目架构

```
PythonMVP/
├── app/                        # 主应用包
│   ├── api/                    # API 路由层
│   │   ├── api.py              # 路由注册中心
│   │   ├── deps.py             # 依赖注入（认证、数据库会话）
│   │   └── endpoints/          # 各业务接口
│   │       ├── auth.py         # 登录认证（JWT）
│   │       ├── codegen.py      # 代码生成器（表元数据、模板、预览/下载/保存）
│   │       ├── items.py        # CRUD 示例（带分页验证）
│   │       ├── install.py      # 系统安装向导
│   │       └── tasks.py        # 后台任务管理
│   ├── core/                   # 核心模块
│   │   ├── config.py           # 全局配置（从 .env 读取）
│   │   ├── database.py         # 异步数据库引擎
│   │   ├── lifespan.py         # 应用生命周期（启动/关闭）
│   │   ├── scheduler.py        # 后台任务调度引擎（APScheduler）
│   │   └── security.py         # 密码哈希、JWT、管理员管理
│   ├── models/                 # 数据库模型（SQLModel）
│   │   └── models.py           # User, Item, TaskLog, TaskConfig
│   ├── schemas/                # 请求/响应数据结构
│   │   ├── schemas.py          # DTO 定义
│   │   └── responses.py        # 统一响应格式 resp_ok / resp_err
│   └── tasks/                  # 后台任务目录（自动发现）
│       └── heartbeat.py        # 示例：系统心跳检测
├── alembic/                    # 数据库迁移
├── static/                     # 前端页面（Vue 3 + TailwindCSS）
│   ├── index.html              # 主仪表盘
│   ├── codegen.html            # 代码生成器
│   ├── install.html            # 安装向导
│   └── tasks.html              # 任务监控面板
├── main.py                     # FastAPI 应用入口
├── run.py                      # 开发助手脚本
├── test_main.py                # 自动化测试
├── requirements.txt            # Python 依赖
├── Dockerfile                  # Docker 镜像
└── docker-compose.yml          # Docker Compose 编排
```

---

## 配置说明

所有配置通过 `.env` 文件管理（安装向导会自动生成），也可手动编辑：

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| `DATABASE_URL` | 数据库连接 | `sqlite:///database.db` |
| `SECRET_KEY` | JWT 签名密钥（安装时自动生成） | - |
| `ALGORITHM` | JWT 算法 | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟） | `30` |
| `FIRST_SUPERUSER` | 管理员用户名 | `admin` |
| `FIRST_SUPERUSER_PASSWORD` | 管理员密码 | `admin` |
| `CORS_ORIGINS` | 允许的跨域来源（逗号分隔） | `http://localhost:8000` |
| `LOG_LEVEL` | 日志级别（DEBUG/INFO/WARNING） | `INFO` |

**安全提示**：生产环境务必修改 `SECRET_KEY` 和管理员密码，不要使用默认值。

---

## 常用命令

```bash
python run.py dev     # 启动开发服务器（带热重载）
python run.py test    # 运行自动化测试
python run.py mig     # 生成并执行数据库迁移
python run.py help    # 查看帮助
```

---

## 技术栈

| 层级 | 技术 |
|------|------|
| Web 框架 | FastAPI 0.128 (async) |
| ORM | SQLModel + SQLAlchemy 2.0 (async) |
| 数据库 | SQLite（开发）/ PostgreSQL（生产） |
| 认证 | JWT (python-jose) + bcrypt |
| 后台任务 | APScheduler (AsyncIOScheduler) |
| 数据库迁移 | Alembic |
| 前端 | Vue 3 + TailwindCSS + DaisyUI |
| 部署 | Docker / Docker Compose |

---

## API 概览

### 认证
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/token` | - | 登录获取 JWT Token |
| GET | `/api/v1/auth/me` | 需要 | 获取当前用户信息 |

### 物品管理（CRUD 示例）
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/items/` | - | 物品列表（公开，支持搜索分页） |
| POST | `/api/v1/items/` | 需要 | 创建物品 |
| GET | `/api/v1/items/{id}` | - | 获取物品详情 |
| PATCH | `/api/v1/items/{id}` | 需要 | 更新物品 |
| DELETE | `/api/v1/items/{id}` | 需要 | 删除物品 |

### 后台任务
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/tasks/configs` | 需要 | 获取后台任务列表 |
| PATCH | `/api/v1/tasks/configs/{id}` | 需要 | 修改任务配置 |
| POST | `/api/v1/tasks/run/{id}` | 需要 | 手动触发任务 |
| GET | `/api/v1/tasks/logs` | 需要 | 任务执行日志（分页） |

### 代码生成器
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/codegen/tables` | 需要 | 列出可用业务表（自动过滤系统表） |
| POST | `/api/v1/codegen/preview` | 需要 | 预览生成的 Endpoint / Schema / 前端代码 |
| POST | `/api/v1/codegen/download` | 需要 | 下载单个生成的代码文件 |
| POST | `/api/v1/codegen/save` | 需要 | 一键保存到项目并自动注册路由 |

### 系统安装
| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| GET | `/api/v1/install/check` | - | 检查安装状态 |
| POST | `/api/v1/install/setup` | - | 执行系统安装 |

启动后也可访问交互式文档：[http://localhost:8000/docs](http://localhost:8000/docs)

---

## 常见问题

**Q: 启动后访问页面一直跳转到安装页？**
A: 这说明 `.env` 文件不存在。完成安装向导或手动创建 `.env` 文件即可。

**Q: 代码生成器里看不到我新建的表？**
A: 确保你已经运行了 `python run.py mig` 同步到数据库，且表名不是系统保留名（`user`、`tasklog`、`taskconfig`）。

**Q: 代码生成器保存后访问新页面报 404？**
A: 保存后需要**重启服务**（`Ctrl+C` 后重新 `python run.py dev`），路由才会生效。

**Q: 已登录但访问任务监控页提示要重新登录？**
A: Token 可能已过期。重新登录即可，登录状态在所有页面间共享。

**Q: 生产环境怎么部署？**
A: 修改 `.env` 中的 `DATABASE_URL` 为 PostgreSQL 地址，修改 `SECRET_KEY` 和管理员密码，然后使用 `docker-compose up -d`。
