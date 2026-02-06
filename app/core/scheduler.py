import importlib
import pkgutil
import time
import logging
import traceback
import os
from datetime import datetime, timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession
from functools import wraps
from sqlmodel import select
from contextvars import ContextVar

from app.core.database import async_session_maker, engine
from app.models.models import TaskLog, TaskConfig
import app.tasks

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# 任务输出上下文 (ContextVar 确保在并发执行时日志不会混淆)
task_output_context: ContextVar[list] = ContextVar("task_output", default=None)

# 全局任务注册表
task_registry = {}

def task_print(message: str):
    """任务专用打印函数，内容将记录到数据库"""
    buffer = task_output_context.get()
    if buffer is not None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        buffer.append(f"[{timestamp}] {message}")

def register_task(label: str):
    """任务注册装饰器"""
    def decorator(func):
        task_id = func.__name__
        task_registry[task_id] = {"func": func, "label": label}
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def task_wrapper(task_id: str):
    """任务执行包装器：处理日志、耗时、状态和上下文"""
    async def wrapper():
        task_info = task_registry.get(task_id)
        if not task_info: return
        
        task_func = task_info["func"]
        task_label = task_info["label"]
        
        log_buffer = []
        token = task_output_context.set(log_buffer)
        
        start_time = time.perf_counter()
        status = "SUCCESS"
        error_msg = None
        
        try:
            await task_func()
        except Exception as e:
            status = "FAILED"
            error_msg = traceback.format_exc()
            logger.error(f"❌ 任务 {task_id} 执行失败: {str(e)}")
        finally:
            duration = time.perf_counter() - start_time
            captured_output = "\n".join(log_buffer) if log_buffer else None
            
            async with async_session_maker() as session:
                session.add(TaskLog(
                    task_name=f"{task_label} ({task_id})",
                    status=status,
                    execution_time=round(duration, 4),
                    output=captured_output,
                    error_message=error_msg
                ))
                await session.commit()
            task_output_context.reset(token)
    return wrapper

async def sync_scheduler_with_db():
    """将数据库配置同步到 APScheduler 内存调度器"""
    async with async_session_maker() as session:
        # 1. 自动同步代码中的新任务到数据库
        result = await session.execute(select(TaskConfig))
        db_configs = result.scalars().all()
        db_ids = {c.id for c in db_configs}

        for tid, info in task_registry.items():
            if tid not in db_ids:
                new_conf = TaskConfig(id=tid, label=info["label"], is_active=True)
                session.add(new_conf)
                await session.commit()
                print(f"✨ 发现新后台任务并入库: {tid}")

        # 2. 根据数据库最新状态重建调度队列
        result = await session.execute(select(TaskConfig))
        latest_configs = result.scalars().all()

        for config in latest_configs:
            # 清除旧计划
            if scheduler.get_job(config.id):
                scheduler.remove_job(config.id)
            
            # 如果启用且代码中存在，则添加
            if config.is_active and config.id in task_registry:
                try:
                    val = float(config.trigger_value)
                    scheduler.add_job(
                        task_wrapper(config.id),
                        "interval",
                        minutes=val,
                        id=config.id,
                        name=config.label,
                        replace_existing=True
                    )
                except Exception as e:
                    logger.error(f"任务 {config.id} 调度配置无效: {e}")

def start_scheduler():
    """启动调度引擎并自动扫描任务目录"""
    import app.tasks as tasks_pkg
    tasks_dir = os.path.dirname(os.path.abspath(tasks_pkg.__file__))
    
    # 强制导入所有任务模块，触发装饰器注册
    for loader, module_name, is_pkg in pkgutil.walk_packages([tasks_dir], "app.tasks."):
        importlib.import_module(module_name)

    scheduler.start()
    logger.info("🚀 后台调度引擎已启动")

def shutdown_scheduler():
    """安全关闭调度引擎"""
    scheduler.shutdown()
    logger.info("🛑 后台调度引擎已关闭")
