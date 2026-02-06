# 使用官方 Python 3.11 轻量级镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
# 防止 Python 生成 .pyc 文件
ENV PYTHONDONTWRITEBYTECODE=1
# 确保控制台输出不被缓冲
ENV PYTHONUNBUFFERED=1
# 设置 Python 路径
ENV PYTHONPATH=/app

# 安装系统依赖 (如果需要编译某些库，如 psycopg2，可能需要 gcc 等)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令 (使用 uvicorn 运行 main.py)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
