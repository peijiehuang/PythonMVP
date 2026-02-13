import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import os
import logging

from app.core.config import settings
from app.core.lifespan import lifespan
from app.api.api import api_router
from app.schemas.responses import resp_err

# --- 1. 日志与基础配置 ---

logging.basicConfig(level=settings.LOG_LEVEL, format=settings.LOG_FORMAT)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME, 
    version=settings.VERSION,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# --- 2. 安装检测中间件 ---

# 应用级安装状态标志，避免每次请求都检测文件系统
_installed = os.path.exists(".env")

def mark_installed():
    """安装完成后调用，更新内存标志"""
    global _installed
    _installed = True

@app.middleware("http")
async def check_installation(request: Request, call_next):
    # 如果检测到没有安装
    if not _installed:
        path = request.url.path
        # 允许访问安装页面、静态资源和安装接口
        if path not in ["/install", "/api/v1/install/setup", "/api/v1/install/check"] and not path.startswith("/static"):
            return RedirectResponse(url="/install")
    return await call_next(request)

# --- 3. 全局异常捕捉 ---

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=resp_err(message=str(exc.detail))
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"发生未处理异常: {str(exc)}", exc_info=True)
    # 仅在 DEBUG 模式下返回异常详情，生产环境隐藏内部信息
    if settings.LOG_LEVEL.upper() == "DEBUG":
        message = f"服务器内部错误: {str(exc)}"
    else:
        message = "服务器内部错误，请稍后重试"
    return JSONResponse(
        status_code=500,
        content=resp_err(message=message)
    )

# --- 4. 中间件与路由 ---

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# 注册安装完成回调，使中间件标志能及时更新
from app.api.endpoints.install import set_mark_installed_callback
set_mark_installed_callback(mark_installed)

# --- 5. 静态文件与安装入口 ---

@app.get("/install")
async def get_install_page():
    """安装向导页面"""
    return FileResponse("static/install.html")

@app.get("/codegen")
async def get_codegen_page():
    """代码生成器页面"""
    return FileResponse("static/codegen.html")

@app.get("/")
async def read_index():
    if os.path.exists("static/index.html"):
        return FileResponse("static/index.html")
    return {"message": f"Welcome to {settings.PROJECT_NAME}"}

if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
