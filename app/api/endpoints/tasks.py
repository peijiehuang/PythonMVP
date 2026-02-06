from fastapi import APIRouter, Query, HTTPException, Body
from sqlmodel import select, desc, func
from typing import List, Optional
from datetime import datetime
import logging
from sqlalchemy import delete

from app.api.deps import SessionDep, CurrentUser
from app.core.scheduler import scheduler, sync_scheduler_with_db, task_registry, task_wrapper
from app.models.models import TaskLog, TaskConfig
from app.schemas.responses import resp_ok, resp_err

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/configs")
async def get_task_configs(session: SessionDep, user: CurrentUser):
    """获取所有任务的汇总状态"""
    try:
        # 获取数据库配置
        result = await session.execute(select(TaskConfig))
        configs = result.scalars().all()
        
        combined_data = []
        for conf in configs:
            # 查找该任务的最后一条日志
            log_stmt = select(TaskLog).where(
                TaskLog.task_name.like(f"%({conf.id})%")
            ).order_by(desc(TaskLog.created_at)).limit(1)
            log_res = await session.execute(log_stmt)
            last_log = log_res.scalars().first()
            
            # 检查内存调度器状态
            job = scheduler.get_job(conf.id)
            
            combined_data.append({
                "id": conf.id,
                "label": conf.label,
                "trigger_type": conf.trigger_type,
                "trigger_value": conf.trigger_value,
                "is_active": conf.is_active,
                "updated_at": conf.updated_at,
                "last_run": last_log.created_at if last_log else None,
                "last_status": last_log.status if last_log else "NEVER",
                "next_run": job.next_run_time if job else None
            })
        return resp_ok(data=combined_data)
    except Exception as e:
        logger.error(f"Task configs API Error: {e}", exc_info=True)
        return resp_err(message="获取任务列表失败")

@router.patch("/configs/{task_id}")
async def update_task_config(
    task_id: str,
    session: SessionDep,
    user: CurrentUser,
    label: Optional[str] = Body(None),
    is_active: Optional[bool] = Body(None),
    trigger_value: Optional[str] = Body(None)
):
    """更新任务配置并立即热同步"""
    config = await session.get(TaskConfig, task_id)
    if not config:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if label is not None: config.label = label
    if is_active is not None: config.is_active = is_active
    if trigger_value is not None: config.trigger_value = trigger_value
    
    config.updated_at = datetime.now()
    session.add(config)
    await session.commit()
    
    await sync_scheduler_with_db()
    return resp_ok(message="设置已应用")

@router.post("/run/{task_id}")
async def run_task_once(task_id: str, user: CurrentUser):
    """手动单次触发任务"""
    if task_id not in task_registry:
        raise HTTPException(status_code=404, detail="代码中未定义此任务")
    
    func = task_wrapper(task_id)
    import asyncio
    asyncio.create_task(func())
    return resp_ok(message="已触发手动执行")

@router.get("/jobs")
async def get_raw_jobs(user: CurrentUser):
    """获取调度器原始 Job 列表 (调试用)"""
    return resp_ok(data=[{"id": j.id, "name": j.name} for j in scheduler.get_jobs()])

@router.get("/logs")
async def get_task_logs(
    session: SessionDep, 
    user: CurrentUser, 
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100)
):
    """分页获取任务日志"""
    count_res = await session.execute(select(func.count()).select_from(TaskLog))
    total = count_res.scalar()
    
    offset = (page - 1) * size
    result = await session.execute(select(TaskLog).order_by(desc(TaskLog.created_at)).offset(offset).limit(size))
    
    return resp_ok(data={
        "items": result.scalars().all(),
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size
    })

@router.delete("/logs")
async def clear_task_logs(session: SessionDep, user: CurrentUser):
    """一键清空所有任务执行日志"""
    await session.execute(delete(TaskLog))
    await session.commit()
    return resp_ok(message="所有执行日志已成功清空")