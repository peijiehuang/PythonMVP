# PythonMVP - 安全增强版全栈脚手架

这是一个开箱即用的轻量级全栈 MVP (Minimum Viable Product) 项目模板。它展示了如何使用 Python 现代技术栈构建高性能、**安全**、类型安全且易于扩展的 Web 应用。

## 🔐 安全特性 (Security Features) - NEW!

本项目已集成完整的 **JWT (JSON Web Token)** 鉴权体系：
*   **OAuth2 密码模式**: 标准的 `/token` 登录流程。
*   **密码哈希**: 使用 `bcrypt` 进行加盐哈希存储，拒绝明文密码。
*   **接口保护**: 写入操作 (`POST`, `PATCH`, `DELETE`) 强制要求登录，读取操作默认公开。
*   **前端集成**: 实现了自动 Token 注入、登录模态框、401 自动登出拦截器。

> **默认管理员账号**:
> - Username: `admin`
> - Password: `admin`
> *(系统首次启动时自动创建)*

---

## 🛠 技术栈

### 后端 (Backend)
- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **ORM**: [SQLModel](https://sqlmodel.tiangolo.com/)
- **Auth**: Python-Jose (JWT), Passlib (Bcrypt), OAuth2
- **Database**: SQLite (默认)

### 前端 (Frontend)
- **Core**: Vue.js 3 (Composition API)
- **Styling**: Tailwind CSS + DaisyUI
- **HTTP**: Axios (拦截器处理 Token)

---

## 📂 项目结构说明

```text
d:\Source\AI学习\PythonMVP\
├── main.py                 # 核心：包含鉴权逻辑、User/Item模型、API路由
├── requirements.txt        # 依赖清单 (新增 python-jose, passlib 等)
├── static\                 # 静态资源
│   └── index.html          # 前端 SPA：包含登录弹窗与鉴权逻辑
├── database.db             # SQLite 数据库
└── test_auth_flow.py       # 自动化鉴权测试脚本
```

---

## 🚀 快速开始 (Quick Start)

为了保证开发环境的纯净与依赖隔离，请**务必**使用虚拟环境运行本项目。

### 1. 环境初始化 (Setup)

#### Windows (PowerShell)
```powershell
# 1. 创建虚拟环境 (仅需执行一次)
python -m venv .venv

# 2. 激活环境
.\.venv\Scripts\activate.ps1
```

#### Windows (CMD)
```cmd
:: 1. 创建虚拟环境
python -m venv .venv

:: 2. 激活环境
.\.venv\Scripts\activate.bat
```

#### macOS / Linux
```bash
# 1. 创建虚拟环境
python3 -m venv .venv

# 2. 激活环境
source .venv/bin/activate
```

> **提示**: 激活成功后，命令行提示符前会出现 `(.venv)` 字样。

### 2. 安装依赖
确保虚拟环境已激活，然后执行：
```bash
pip install -r requirements.txt
```

### 3. 启动服务
```bash
python main.py
```
*启动后，系统会自动创建 `database.db` 并初始化 `admin` 用户。*

### 3. 访问应用
*   **Web 界面**: [http://localhost:8000](http://localhost:8000)
    *   尝试点击 "New Item"，会弹出登录框。使用 `admin`/`admin` 登录。
*   **API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)
    *   点击右上角 "Authorize" 按钮，输入账号密码即可解锁受保护接口。

### 4. 运行自动化测试
验证鉴权逻辑是否生效：
```bash
# 确保服务已在后台运行，然后执行：
python test_auth_flow.py
```
预期输出：
```text
[OK] 公开接口 /items/ 访问成功
[OK] 未登录保护生效 (401 Unauthorized)
[OK] 登录成功，获取 Token: ...
[OK] 带 Token 创建物品成功...
```

---

## 💡 开发指南 (Development Guide)

### 🛡️ 接口鉴权指南 (API Security Guide)

FastAPI 通过依赖注入 (`Depends`) 轻松管理接口权限。

#### 1. 允许匿名访问 (Public / Anonymous)
**不需要**添加任何鉴权依赖，任何用户均可访问。

```python
@app.get("/items/public")
def read_public_items():
    # ❌ 无法获取当前用户信息
    return {"msg": "任何人都可以看到这条消息"}
```

#### 2. 需要 Token 访问 (Authenticated)
在路由参数中添加 `current_user: User = Depends(get_current_user)`。
*   如果请求未携带有效 Token，FastAPI 会自动抛出 `401 Unauthorized` 错误。
*   代码块内部可直接使用 `current_user` 对象。

```python
from fastapi import Depends
from main import get_current_user, User

@app.get("/items/protected")
def read_user_items(current_user: User = Depends(get_current_user)):
    # ✅ 此时 current_user 已通过验证
    return {
        "msg": "您已登录",
        "username": current_user.username,
        "user_id": current_user.id
    }
```

#### 🔬 为什么这样写就能保护接口？ (Under the Hood)
当你在参数中声明 `Depends(get_current_user)` 时，FastAPI 会执行以下连锁反应：

1.  **提取 Token**: `get_current_user` 依赖于 `oauth2_scheme`，它会自动检查 HTTP 请求头 `Authorization: Bearer <token>`。
2.  **验证 Token**: 拿到 Token 后，系统尝试用 `SECRET_KEY` 对其进行解码和验证（检查签名、有效期）。
3.  **阻断请求**:
    *   如果 Token **缺失**或**无效**，依赖函数直接抛出 `HTTPException` (401 错误)。
    *   **关键点**：由于异常抛出，**后续的路由函数体根本不会被执行**。这就实现了“保护”。
4.  **注入对象**: 只有验证通过，才会从数据库查询 User 对象并注入给 `current_user` 参数，让你的业务逻辑直接可用。

### 如何获取当前登录用户？
`current_user` 对象即为当前登录的 `User` 数据库模型实例，包含 `id`, `username` 等字段。

---

## 🔒 生产环境注意事项
1.  **修改 SECRET_KEY**: 在 `.env` 文件或环境变量中设置复杂的随机字符串。
2.  **HTTPS**: OAuth2 必须在 HTTPS 下运行以保证安全。
3.  **数据库**: 建议切换到 PostgreSQL。