import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import logging

from app.core.config import settings
from app.core.lifespan import lifespan
from app.api.api import api_router
from app.schemas.responses import resp_err

# --- 1. 日志与基础配置 ---

# 初始化全局日志配置
logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

# 初始化 FastAPI 应用
app = FastAPI(
    title=settings.PROJECT_NAME, 
    version=settings.VERSION,
    lifespan=lifespan, # 挂载生命周期钩子
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- 2. 全局异常捕捉 ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """捕捉并格式化 FastAPI 的 HTTP 异常"""
    return JSONResponse(
        status_code=exc.status_code,
        content=resp_err(message=str(exc.detail))
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """捕捉并格式化全应用未处理的运行时错误"""
    logger.error(f"发生未处理异常: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=resp_err(message=f"服务器内部错误: {str(exc)}")
    )

# --- 3. 中间件与路由 ---

# 跨域资源共享配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 生产环境请修改为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册核心 API 路由模块
app.include_router(api_router, prefix=settings.API_V1_STR)

# --- 4. 静态文件挂载 ---

@app.get("/")
async def read_index():
    """根路径：尝试返回 index.html 演示页面"""
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

# 挂载 /static 目录
if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    # 使用 Uvicorn 启动
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)