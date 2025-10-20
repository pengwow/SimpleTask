"""日志相关的Pydantic模型"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class EnvLogBase(BaseModel):
    """环境日志基础模型"""
    env_id: int = Field(..., description="环境ID")
    level: str = Field(default='INFO', max_length=10, description="日志级别")
    message: str = Field(..., description="日志消息")


class EnvLogResponse(EnvLogBase):
    """环境日志响应模型"""
    id: int = Field(..., description="日志ID")
    timestamp: datetime = Field(..., description="日志时间")
    
    class Config:
        from_attributes = True


class TaskLogBase(BaseModel):
    """任务日志基础模型"""
    execution_id: int = Field(..., description="执行ID")
    level: str = Field(default='INFO', max_length=10, description="日志级别")
    message: str = Field(..., description="日志消息")


class TaskLogResponse(TaskLogBase):
    """任务日志响应模型"""
    id: int = Field(..., description="日志ID")
    timestamp: datetime = Field(..., description="日志时间")
    
    class Config:
        from_attributes = True


class LogQueryParams(BaseModel):
    """日志查询参数模型"""
    level: Optional[str] = Field(None, description="日志级别过滤")
    start_time: Optional[datetime] = Field(None, description="开始时间")
    end_time: Optional[datetime] = Field(None, description="结束时间")
    limit: int = Field(default=100, ge=1, le=1000, description="返回数量限制")
    offset: int = Field(default=0, ge=0, description="偏移量")