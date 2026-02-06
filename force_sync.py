import asyncio
import os
import sys

# 设置环境
sys.path.append(os.getcwd())

async def force_sync():
    print("🚀 正在强制同步后台任务到数据库...")
    from app.core.scheduler import start_scheduler, sync_scheduler_with_db, task_registry
    from app.core.database import create_db_and_tables
    
    # 1. 确保表存在
    await create_db_and_tables()
    
    # 2. 触发模块扫描
    start_scheduler()
    print(f"📦 已注册任务: {list(task_registry.keys())}")
    
    # 3. 执行数据库同步
    await sync_scheduler_with_db()
    print("✅ 同步完成！")

if __name__ == "__main__":
    if os.path.exists(".env"):
        asyncio.run(force_sync())
    else:
        print("❌ 未发现 .env 文件，请先完成安装向导。")
