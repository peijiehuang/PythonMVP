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

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 启动服务
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

## 💡 开发指南

### 如何保护一个新的接口？

在 `main.py` 中，只需在路由函数中添加 `current_user` 依赖：

```python
from fastapi import Depends
from main import get_current_user, User

@router.get("/sensitive-data")
def get_secret(current_user: User = Depends(get_current_user)):
    return {"secret": "只有登录用户能看到我", "user": current_user.username}
```

### 如何获取当前登录用户？
`current_user` 对象即为当前登录的 `User` 数据库模型实例，包含 `id`, `username` 等字段。

---

## 🔒 生产环境注意事项
1.  **修改 SECRET_KEY**: 在 `.env` 文件或环境变量中设置复杂的随机字符串。
2.  **HTTPS**: OAuth2 必须在 HTTPS 下运行以保证安全。
3.  **数据库**: 建议切换到 PostgreSQL。