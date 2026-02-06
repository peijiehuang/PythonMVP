# 🌌 Cosmic MVP - 全栈全异步极速开发框架

**Cosmic MVP** 是一个深度集成的生产级脚手架，专为“极速原型验证”而生。它基于 **FastAPI** + **SQLModel** + **Alembic** 构建，封装了全异步性能与标准化的开发方法论。

---

## 🧭 目录
1. [快速开始：1分钟跑通项目](#快速开始1分钟跑通项目)
2. [后端篇：5分钟交付一个新接口](#后端篇5分钟交付一个新接口)
3. [前端篇：如何增加页面与数据联动](#前端篇如何增加页面与数据联动)
4. [质量篇：自动化测试](#质量篇自动化测试)
5. [部署篇：Docker 与 宝塔面板](#部署篇docker-与-宝塔面板)
6. [进阶篇：性能参考与数据库切换](#进阶篇性能参考与数据库切换)

---

## 快速开始：1分钟跑通项目

### 1. 环境准备 (隔离开发)
**强烈建议**在调试和开发时使用虚拟环境，防止污染本机全局 Python 环境。

#### Windows
```powershell
# 创建虚拟环境
python -m venv .venv
# 激活环境
.\.venv\Scripts\Activate.ps1
# 安装依赖
pip install -r requirements.txt
```

#### Linux / macOS
```bash
# 创建虚拟环境
python3 -m venv .venv
# 激活环境
source .venv/bin/activate
# 安装依赖
pip install -r requirements.txt
```

### 2. 启动项目
框架预置了 `run.py` 脚本，封装了所有复杂操作：
```bash
# 启动全异步开发服务器
python run.py dev
```
- **交互式 API 文档**: [http://localhost:8000/api/v1/docs](http://localhost:8000/api/v1/docs)
- **前端演示页面**: [http://localhost:8000/](http://localhost:8000/)
- **初始账号**: `admin` / `admin` (首次启动自动创建)

---

## 后端篇：5分钟交付一个新接口

开发新功能遵循 **“四步闭环法”**：

### Step 1: 定义数据库模型 (Models)
在 `app/models/models.py` 中添加你的 SQLModel。例如添加一个“任务 Task”：
```python
class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(index=True, description="任务标题")
    is_done: bool = Field(default=False, description="是否完成")
```

### Step 2: 定义数据验证协议 (Schemas)
在 `app/schemas/schemas.py` 中定义输入格式：
```python
class TaskCreate(BaseModel):
    title: str
```

### Step 3: 自动化数据库迁移
无需手动在数据库建表，运行以下命令自动同步：
```bash
python run.py mig
# 输入此次变更的描述，如: "add task table"
```

### Step 4: 编写并注册 API 路由
在 `app/api/endpoints/tasks.py` 编写：
```python
from app.schemas.responses import resp_ok

@router.post("/", response_model=None)
async def create_task(task_in: TaskCreate, session: SessionDep, user: CurrentUser):
    # 自动校验输入并保存
    db_task = Task.model_validate(task_in)
    session.add(db_task)
    await session.commit()
    return resp_ok(data=db_task) # 使用统一响应格式
```
并在 `app/api/api.py` 中 `include_router` 注册该路由。

---

## 前端篇：如何增加页面与数据联动

### 1. 结构建议
- **初学者**: 直接修改 `static/index.html`，使用内置的 Vue3 + Axios 示例。
- **专业开发**: 在 `frontend/` 目录使用 Vite 搭建独立项目，联调 `http://localhost:8000/api/v1`。

### 2. 前后端联调逻辑 (Axios)
框架强制 API 返回格式为 `{ success, data, message }`。
参考 `frontend/api-client-example.js` 中的拦截器逻辑：

```javascript
// 在业务组件中请求数据
const getTasks = async () => {
    // 拦截器会自动过滤掉 success/message，直接返回核心 data 数组
    const tasks = await api.get('/tasks/'); 
    console.log("任务列表:", tasks); 
}
```

### 3. 处理鉴权页面
如果页面需要登录才能访问，拦截器会自动检测 `401` 状态码并引导用户跳转登录页。本地 Token 存储已在示例代码中实现。

---

## 质量篇：自动化测试

**MVP 不代表低质量。** 我们提供了严苛的异步测试环境，使用内存数据库运行：

```bash
# 执行全量自动化测试
python run.py test
```
- **示例代码**: 参考 `test_main.py` 了解如何编写异步测试。
- **特性**: 每次测试前自动建表，测试后自动删表，环境完全隔离。

---

## 部署篇：Docker 与 宝塔面板

### 1. Docker 部署 (生产环境首选)
```bash
# 一键构建镜像并启动容器
docker-compose up -d --build
```
- 自动包含：Python 环境、依赖库、异步驱动配置、本地数据卷挂载。

### 2. 宝塔面板部署 (保姆级教程)
1.  **上传代码**: 将项目打包上传到服务器 `/www/wwwroot/你的项目名`。
2.  **创建项目**:
    - 点击面板左侧【Python项目管理器】 -> 【添加项目】。
    - **启动文件**: 选择 `main.py`。
    - **框架**: 选 `FastAPI` (若无则选 `python`)。
    - **端口**: 填写 `8000`。
3.  **安装依赖**: 勾选【安装模块依赖 (`pip install -r requirements.txt`)】。
4.  **配置代理**:
    - 在【网站】菜单中新建一个站点（绑定你的域名）。
    - 点击【设置】 -> 【反向代理】 -> 【添加反向代理】。
    - 代理名称任意，目标 URL 填写 `http://127.0.0.1:8000`。
    - 现在即可通过你的域名访问 API。

---

## 进阶篇：性能参考与数据库切换

### 1. 真实压测性能
基于本地 SQLite + 异步驱动环境的并发数据：
| 操作类型 | 吞吐量 (RPS) | 平均延迟 | 瓶颈点 |
| :--- | :--- | :--- | :--- |
| **并发查询** | **~220 req/s** | ~210ms | CPU / 内存 |
| **并发写入** | **~60 req/s** | ~280ms | SQLite 文件锁 |

### 2. 无缝切换生产级数据库
当写入压力增大时，只需修改 `.env` 配置文件即可从 SQLite 迁移到 **MySQL** 或 **PostgreSQL**，**无需改动任何 Python 代码**：
```env
# 示例：切换到 PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/dbname
```
框架会自动处理异步协议转换 (`postgresql+asyncpg://`)。

---

## 🔐 初始凭据

系统首次启动时会自动创建一个超级管理员账号。您可以在 `.env` 文件中自定义其账号和密码：

```env
FIRST_SUPERUSER=admin
FIRST_SUPERUSER_PASSWORD=admin
```

> **注意**: 如果数据库中已存在同名用户，系统将不会重复创建或覆盖密码。

---
**Cosmic MVP** - 让您的 Idea 飞得更快。🚀
