import logging
from app.core.scheduler import register_task, task_print

"""
心跳任务示例 (解耦注册版)
使用 @register_task 装饰器即可自动注入到管理系统中
使用 task_print 记录的日志会保存到数据库中供 UI 查看
"""

logger = logging.getLogger(__name__)

@register_task("系统健康心跳")
async def heartbeat():
    """业务逻辑：简单的控制台心跳输出"""
    task_print("💓 异步心跳检测：后台服务存活")
    task_print("📊 正在检查系统资源...")
    # 模拟业务逻辑
    task_print("✅ 资源检查完成，系统状态良好。")
