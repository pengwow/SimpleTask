"""Python环境相关的Pydantic模型"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class PythonEnvBase(BaseModel):
    """Python环境基础模型"""
    name: str = Field(..., max_length=100, description="环境名称")
    python_version: str = Field(default='3.9.21', max_length=20, description="Python版本")
    requirements: Optional[str] = Field(None, description="依赖列表")
    mirror_source_id: Optional[int] = Field(None, description="镜像源ID")


class PythonEnvCreate(PythonEnvBase):
    """创建Python环境的请求模型"""
    pass


class PythonEnvUpdate(BaseModel):
    """更新Python环境的请求模型"""
    name: Optional[str] = Field(None, max_length=100, description="环境名称")
    requirements: Optional[str] = Field(None, description="依赖列表")
    mirror_source_id: Optional[int] = Field(None, description="镜像源ID")


class PythonEnvResponse(PythonEnvBase):
    """Python环境响应模型"""
    id: int = Field(..., description="环境ID")
    status: str = Field(..., description="环境状态")
    path: str = Field(..., description="环境路径")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class PythonEnvWithDetails(PythonEnvResponse):
    """带详细信息的Python环境响应模型"""
    mirror_source_name: Optional[str] = Field(None, description="镜像源名称")
    active_tasks_count: int = Field(0, description="活跃任务数量")