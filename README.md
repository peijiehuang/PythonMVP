# 🌌 Cosmic MVP - 全栈极速开发框架 (v3.8 易用增强版)

**Cosmic MVP** 是一个专为“想快速把想法变成产品”的开发者设计的脚手架。  
它不仅是一个后端框架，更是一套**完整的生产力方案**：自带安装向导、自带后台任务监控、自带漂亮的 UI 界面。

---

## 🧭 快速索引
- [🚩 小白避坑指南（必看！）](#-小白避坑指南必看)
- [🚀 3分钟快速上手](#-3分钟快速上手)
- [🛠️ 怎么开发一个新功能？(保姆级教程)](#️-怎么开发一个新功能保姆级教程)
- [⏰ 怎么写后台定时任务？](#-怎么写后台定时任务)
- [📂 目录结构（大白话版）](#-目录结构大白话版)

---

## 🚩 小白避坑指南（必看！）

在开发过程中，请务必记住以下几点，能帮你节省 80% 的排错时间：

1.  **Python 的“等一等” (`await`)**：  
    本项目是异步框架。只要你操作数据库（例如 `session.add`, `session.commit`），前面**必须**写 `await`。  
    ❌ 错误：`session.commit()`  
    ✅ 正确：`await session.commit()`

2.  **修改代码后要“同步”数据库**：  
    如果你在 `models.py` 里增加了一个字段或一个新表，数据库并不会自动感知。  
    你**必须**在命令行运行：`python run.py mig`，然后按提示输入一个名字。

3.  **注意缩进！**  
    Python 对缩进非常敏感。如果报错 `IndentationError`，请检查你的代码行首是否有乱入的空格。

4.  **管理员登录**：  
    默认账号/密码是 `admin` / `admin`。如果你忘了，删除文件夹里的 `.env` 文件重新刷新页面即可重设。

---

## 🚀 3分钟快速上手

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
启动后访问：[http://localhost:8000/install](http://localhost:8000/install)  
点点鼠标，设置一下管理员，你就拥有了一个完整的系统。

---

## 🛠️ 怎么开发一个新功能？(保姆级教程)

假设你想做一个“笔记记录”功能：

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

---

## ⏰ 怎么写后台定时任务？

Cosmic MVP 的后台任务是“即插即用”的：

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
    你会发现“自动清理垃圾记录”已经出现在列表里了，你可以随便改它的执行频率。

---

## 📂 目录结构（大白话版）

- **`app/api/`**: 所有的接口（URL路径）都在这里。
- **`app/models/`**: 数据库长什么样，都在这里定义。
- **`app/tasks/`**: 所有的定时任务放在这里。
- **`static/`**: 网页前端页面。
- **`run.py`**: **你的万能助手**。运行 `python run.py` 看看它能帮你做什么。

---
**提示**：如果你在开发中遇到任何困难，请查看 `/static/tasks.html` 中的日志输出，那里有最详细的报错提示。🚀
