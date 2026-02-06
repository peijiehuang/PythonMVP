# 🌌 Cosmic MVP - 全栈全异步极速开发框架 (v3.5)

**Cosmic MVP** 是一款专为独立开发者和初创团队设计的“保姆级”开发脚手架。它融合了 **FastAPI** 的极致速度、**SQLModel** 的简洁开发体验以及 **Alembic** 的严谨数据库治理。

核心目标：**让您把 90% 的精力花在业务逻辑上，剩下的 10% 交给框架。**

---

## 🧭 目录
- [🎯 核心优势](#-核心优势)
- [📂 项目结构全景图](#-项目结构全景图)
- [🚀 快速开始：1分钟跑通项目](#-快速开始1分钟跑通项目)
- [🏗️ 后端开发：标准四步开发法](#-后端开发标准四步开发法)
- [⏰ 后台服务：可视化插件式任务系统](#-后台服务可视化插件式任务系统)
- [🎨 前端开发：前后端联动实战](#-前端开发前后端联动实战)
- [🧪 质量保障：自动化测试](#-质量保障自动化测试)
- [📡 生产部署：Docker与宝塔面板](#-生产部署docker与宝塔面板)
- [💡 常见问题排查 (FAQ)](#-常见问题排查-faq)

---

## 🎯 核心优势

- **全异步设计**: 从数据库驱动 (aiosqlite) 到接口处理，全链路非阻塞，性能远超同步框架。
- **智能安装向导**: 告别手动修改 `.env`。首次启动访问 Web 界面即可完成系统配置。
- **插件式任务系统**: 只需在指定目录写代码，任务自动入库、自动显示在管理页面。
- **统一响应协议**: 无论是业务成功还是程序崩溃，前端收到的永远是标准 JSON 格式。
- **开发脚本化**: `run.py` 封装了一切常用命令，无需记忆复杂的 CLI 参数。

---

## 📂 项目结构全景图

理解目录结构是精通框架的第一步：

```text
├── alembic/             # 数据库迁移记录（版本管理）
├── app/
│   ├── api/             # 接口层
│   │   ├── endpoints/   # 具体的业务接口（如：用户、物品、任务管理）
│   │   ├── api.py       # 路由主汇总入口
│   │   └── deps.py      # 核心依赖注入（数据库会话、当前登录用户）
│   ├── core/            # 系统内核
│   │   ├── config.py    # 强类型配置管理（BaseSettings）
│   │   ├── database.py  # 异步数据库引擎与连接池
│   │   ├── security.py  # JWT 加密与密码哈希工具
│   │   ├── scheduler.py # 异步任务调度引擎
│   │   └── lifespan.py  # 应用启动/关闭时的钩子函数
│   ├── models/          # 数据库物理表模型 (SQLModel)
│   ├── schemas/         # 数据传输协议 (Pydantic & 统一响应模型)
│   └── tasks/           # 后台定时任务插件目录
├── static/              # 静态资源（含安装向导、内置仪表盘 Demo）
├── frontend/            # 前端示例与拦截器配置
├── main.py              # 程序主启动文件
├── run.py               # 🚀 万能开发脚本（推荐使用）
└── test_main.py         # 全自动异步测试脚本
```

---

## 🚀 快速开始：1分钟跑通项目

### 1. 环境隔离 (重要)
```powershell
# Windows
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 启动智能安装
执行以下命令开启开发服务器：
```bash
python run.py dev
```
启动后，浏览器访问：[http://localhost:8000/install](http://localhost:8000/install)

**您只需在页面上：**
1. 输入项目名称。
2. 设置您的管理员账号和密码。
3. 系统将自动生成 `.env` 密钥并同步数据库。

---

## 🏗️ 后端开发：标准四步开发法

假设我们要增加一个“反馈 (Feedback)”功能：

### 第一步：定义模型 (`app/models/models.py`)
```python
class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    content: str = Field(description="反馈内容")
    user_id: int = Field(foreign_key="user.id")
```

### 第二步：定义验证协议 (`app/schemas/schemas.py`)
```python
class FeedbackCreate(BaseModel):
    content: str
```

### 第三步：自动同步数据库
```bash
python run.py mig
# 输入: "add feedback"
```

### 第四步：编写业务路由 (`app/api/endpoints/feedback.py`)
```python
@router.post("/")
async def post_feedback(data: FeedbackCreate, session: SessionDep, user: CurrentUser):
    # SessionDep 自动提供数据库连接，CurrentUser 自动获取登录人
    new_fb = Feedback.model_validate(data, update={"user_id": user.id})
    session.add(new_fb)
    await session.commit()
    return resp_ok(data=new_fb) # 统一格式返回
```

---

## ⏰ 后台服务：可视化插件式任务系统

Cosmic MVP 让后台开发变得前所未有的简单：

1.  **极简开发**: 在 `app/tasks/` 下新建 `cleaner.py`。
2.  **自动注入**:
    ```python
    from app.core.scheduler import register_task, task_print

    @register_task("过期数据清理")
    async def clean_job():
        task_print("开始扫描...") # 日志会出现在网页端
        # 业务逻辑...
        task_print("清理完成 ✅")
    ```
3.  **实时管控**: 在主页点击“时钟图标”，您可以：
    - **热修改频率**: 在网页上改个数字（如从 10 分钟改为 1 分钟），立即生效。
    - **实时日志**: 每一秒的任务运行状态、耗时、报错信息全掌握。

---

## 🎨 前端开发：前后端联动实战

### 1. 响应结构
无论成功还是失败，接口返回格式永远固定：
`{ "success": true, "data": ..., "message": "..." }`

### 2. 前端拦截器示例 (`frontend/api-client-example.js`)
我们为您封装好了 Axios 拦截器，使用它开发页面：
```javascript
import api from './api-client-example';

// 拿到的是直接的业务对象数据，不再需要 .data.data
const me = await api.get('/auth/me');
console.log("当前用户:", me.username);
```

---

## 🧪 质量保障：自动化测试

**MVP 不代表马虎。** 在提交代码前，请确保测试通过：
```bash
python run.py test
```
该命令会自动创建一个内存中的“临时数据库”，模拟真实请求流程，确保您的增删查改逻辑完全正确。

---

## 📡 生产部署：Docker与宝塔面板

### 1. Docker 部署 (生产环境)
```bash
docker-compose up -d --build
```

### 2. 宝塔面板部署 (小白指南)
1.  上传项目文件。
2.  打开“Python项目管理器”，点击“添加项目”。
3.  **启动文件**选 `main.py`，端口填 `8000`。
4.  在“反向代理”中将域名指向 `http://127.0.0.1:8000`。
5.  访问域名，进入安装向导，完成部署。

---

## 💡 常见问题排查 (FAQ)

- **Q: 为什么我访问接口报 404？**
  - **A**: 请检查 URL 是否带有 `/api/v1` 前缀。
- **Q: 为什么后台任务没有运行？**
  - **A**: 请在管理页面确认该任务的“启用”开关已打开。
- **Q: 如何修改管理员密码？**
  - **A**: 删除根目录下的 `.env` 文件并刷新页面，重新进入安装向导（业务数据会保留）。
- **Q: 数据库被锁定了怎么办？**
  - **A**: SQLite 在极高并发写入时会锁定。如果业务量大，请在 `.env` 中将 `DATABASE_URL` 切换为 PostgreSQL。

---
**Cosmic MVP** - 愿您的每个 Idea 都能以最快、最稳的方式惊艳世界。🚀