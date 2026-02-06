from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

"""
数据库物理模型定义 (SQLModel)
这些类会直接映射为数据库表。
"""

class User(SQLModel, table=True):
    """用户表模型"""
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, description="用户名（唯一）")
    hashed_password: str = Field(description="加盐后的密码哈希")
    is_active: bool = Field(default=True, description="用户状态")

class Item(SQLModel, table=True):
    """物品表模型（业务示例）"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=255, schema_extra={"example": "Apple Stock"})
    description: Optional[str] = Field(default=None, schema_extra={"example": "Tech Giant"})
    is_active: bool = Field(default=True)
    
    # 自动生成的时间戳
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="创建时间"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="更新时间"
    )

class TaskLog(SQLModel, table=True):
    """后台任务执行日志表"""
    id: Optional[int] = Field(default=None, primary_key=True)
    task_name: str = Field(index=True, description="任务名称")
    status: str = Field(description="执行状态 (SUCCESS/FAILED)")
    execution_time: float = Field(description="执行耗时(秒)")
    output: Optional[str] = Field(default=None, description="业务日志输出")
    error_message: Optional[str] = Field(default=None, description="错误堆栈信息")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TaskConfig(SQLModel, table=True):
    """后台任务配置表"""
    id: Optional[str] = Field(primary_key=True, description="任务唯一标识(函数名)")
    label: str = Field(description="任务显示名称")
    trigger_type: str = Field(default="interval", description="触发类型: interval/cron")
    trigger_value: str = Field(default="5", description="触发值: 分钟数或cron表达式")
    is_active: bool = Field(default=True, description="是否启用")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))