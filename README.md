# PythonMVP - 现代全栈快速开发脚手架

这是一个开箱即用的轻量级全栈 MVP (Minimum Viable Product) 项目模板。它展示了如何使用 Python 现代技术栈构建高性能、类型安全且易于扩展的 Web 应用。

## 🛠 技术栈

### 后端 (Backend)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/) (高性能异步 Web 框架)
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/) (结合 SQLAlchemy 与 Pydantic 的最佳实践)
- **Validation**: Pydantic v2 (严格的数据验证)
- **Database**: SQLite (默认，可轻松切换至 PostgreSQL/MySQL)

### 前端 (Frontend)
- **Core**: [Vue.js 3](https://vuejs.org/) (Composition API)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) + [DaisyUI](https://daisyui.com/)
- **HTTP Client**: Axios
- **Architecture**: No-Build (无需 Node.js/Webpack 构建过程，由后端直接托管静态资源)

---

## 📂 项目结构说明

```text
d:\Source\AI学习\PythonMVP\
├── main.py                 # 核心入口：包含所有后端逻辑（模型、数据库、路由、配置）
├── requirements.txt        # Python 依赖清单
├── static\                 # 静态资源目录
│   └── index.html          # 前端单页应用 (Vue3 + Tailwind)入口
├── database.db             # SQLite 数据库文件 (自动生成)
└── README.md               # 项目说明文档
```

### 核心文件解析

1.  **`main.py`**:
    *   **基础设施**: 配置日志、数据库连接 (`engine`)、生命周期管理 (`lifespan`).
    *   **数据模型**: 定义了 `Item` (数据库表) 以及对应的 DTO (`ItemCreate`, `ItemRead`)，实现了 **读写分离** 的模型设计。
    *   **API 路由**: 实现了标准的 RESTful CRUD 接口 (`GET`, `POST`, `PATCH`, `DELETE`).
    *   **静态托管**: 挂载 `/static` 目录并提供根路径 `/` 访问 `index.html`。

2.  **`static/index.html`**:
    *   一个完整的单页应用 (SPA)。
    *   使用 `<script setup>` 风格编写 Vue 逻辑。
    *   实现了数据的列表展示、搜索、新建模态框、编辑和删除功能。

---

## 🚀 快速开始

### 1. 环境准备
确保已安装 Python 3.9+。

### 2. 安装依赖
在项目根目录下运行：
```bash
pip install -r requirements.txt
```

### 3. 启动服务
直接运行 `main.py` 或使用 `uvicorn`：
```bash
# 方式 A (推荐开发使用)
python main.py

# 方式 B (生产模式)
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
*启动后，系统会自动创建 `database.db` 数据库文件。*

### 4. 访问应用
*   **Web 界面**: [http://localhost:8000](http://localhost:8000)
*   **API 文档 (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **API 调试 (ReDoc)**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 💡 二次开发指南 (如何加功能)

本项目的优势在于**修改即生效**，非常适合快速迭代。

### 场景 A：添加一个新的 API 方法 (Function)

**目标**：添加一个 "统计所有物品数量" 的接口。

1.  打开 `main.py`。
2.  在 `router` 区域添加新函数：
    ```python
    from sqlmodel import func

    @router.get("/stats/count", summary="获取物品总数")
    def count_items(session: Session = Depends(get_session)):
        count = session.exec(select(func.count(Item.id))).one()
        return {"total_items": count}
    ```
3.  保存文件，服务会自动重载。
4.  访问 `/docs` 即可看到新接口。

---


### 场景 B：添加一个新的数据实体 (Entity)

**目标**：添加 "用户 (User)" 模块。

1.  **定义模型 (`main.py`)**:
    ```python
    class User(SQLModel, table=True):
        id: Optional[int] = Field(default=None, primary_key=True)
        username: str
        email: str
    ```
2.  **注册表结构**: 重启应用时，`SQLModel.metadata.create_all(engine)` 会自动创建新表。
3.  **编写 CRUD**: 参考 `Item` 的 CRUD 逻辑复制一份，修改为 `User` 模型。

---


### 场景 C：添加一个新的页面 (Page)

由于本项目采用后端托管静态文件的方式，添加页面有两种策略：

#### 策略 1：独立页面 (推荐简单场景)
1.  在 `static/` 目录下新建 `dashboard.html` (可以复制 `index.html` 修改)。
2.  在 `main.py` 中添加路由映射：
    ```python
    @app.get("/dashboard")
    async def read_dashboard():
        return FileResponse("static/dashboard.html")
    ```
3.  访问 `http://localhost:8000/dashboard`。

#### 策略 2：前端路由 (Vue Router)
如果需要复杂的单页应用体验，建议在 `index.html` 中引入 `vue-router` CDN，并修改前端逻辑接管 URL 变化，后端只需保留 `root` 路由即可。

---


## 🔒 最佳实践提示
1.  **数据库迁移**: 当前使用自动建表。生产环境建议引入 `alembic` 做版本管理。
2.  **安全性**: 当前 API 未包含鉴权。建议添加 OAuth2 或 JWT Token 验证 (FastAPI 内置支持)。
3.  **CORS**: 默认允许所有跨域 (`allow_origins=["*"]`)，上线前请修改为特定域名。
