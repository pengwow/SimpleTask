"""任务相关的Pydantic模型"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """任务基础模型"""
    name: str = Field(..., max_length=100, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    project_id: Optional[int] = Field(None, description="项目ID")
    python_env_id: int = Field(..., description="Python环境ID")
    command: str = Field(..., description="执行命令")
    schedule_type: str = Field(..., description="调度类型")  # immediate, interval, one-time, cron
    schedule_config: str = Field(..., description="调度配置（JSON格式）")
    max_instances: int = Field(default=1, description="最大并发实例数")
    is_active: bool = Field(default=False, description="是否激活")


class TaskCreate(TaskBase):
    """创建任务的请求模型"""
    pass


class TaskUpdate(BaseModel):
    """更新任务的请求模型"""
    name: Optional[str] = Field(None, max_length=100, description="任务名称")
    description: Optional[str] = Field(None, description="任务描述")
    project_id: Optional[int] = Field(None, description="项目ID")
    command: Optional[str] = Field(None, description="执行命令")
    schedule_type: Optional[str] = Field(None, description="调度类型")
    schedule_config: Optional[str] = Field(None, description="调度配置")
    max_instances: Optional[int] = Field(None, description="最大并发实例数")
    is_active: Optional[bool] = Field(None, description="是否激活")


class TaskResponse(TaskBase):
    """任务响应模型"""
    id: int = Field(..., description="任务ID")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class TaskWithDetails(TaskResponse):
    """带详细信息的任务响应模型"""
    project_name: Optional[str] = Field(None, description="项目名称")
    python_env_name: str = Field(..., description="Python环境名称")
    running_instances: int = Field(0, description="运行中实例数")
    

class TaskExecutionBase(BaseModel):
    """任务执行基础模型"""
    task_id: int = Field(..., description="任务ID")
    status: str = Field(..., description="执行状态")


class TaskExecutionResponse(TaskExecutionBase):
    """任务执行响应模型"""
    id: int = Field(..., description="执行ID")
    start_time: datetime = Field(..., description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    duration: Optional[float] = Field(None, description="执行耗时（秒）")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        from_attributes = True


class TaskExecutionWithDetails(TaskExecutionResponse):
    """带详细信息的任务执行响应模型"""
    task_name: str = Field(..., description="任务名称")
    python_env_name: str = Field(..., description="Python环境名称")


class TaskActionResponse(BaseModel):
    """任务操作响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    task_id: Optional[int] = Field(None, description="任务ID")
    execution_id: Optional[int] = Field(None, description="执行ID")


class TaskListResponse(BaseModel):
    """任务列表响应模型，包含分页信息"""
    success: bool = Field(..., description="操作是否成功")
    data: List[TaskWithDetails] = Field(..., description="任务列表")
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    per_page: int = Field(..., description="每页记录数")
    total_pages: int = Field(..., description="总页数")