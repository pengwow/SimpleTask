"""项目相关的Pydantic模型"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# 移除了ProjectTag相关模型，标签将作为字符串列表存储


class ProjectBase(BaseModel):
    """项目基础模型"""
    name: str = Field(..., max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    work_path: str = Field(default='/', description="工作路径")
    source_type: str = Field(default='zip', description="源码类型")
    source_url: Optional[str] = Field(None, description="源码URL")
    branch: str = Field(default='main', description="Git分支")
    git_username: Optional[str] = Field(None, description="Git用户名")
    git_password: Optional[str] = Field(None, description="Git密码")


class ProjectCreate(ProjectBase):
    """创建项目的请求模型"""
    tags: Optional[List[str]] = Field(default=[], description="标签列表")


class ProjectUpdate(BaseModel):
    """更新项目的请求模型"""
    name: Optional[str] = Field(None, max_length=100, description="项目名称")
    description: Optional[str] = Field(None, description="项目描述")
    tags: Optional[List[str]] = Field(None, description="标签列表")


class ProjectResponse(ProjectBase):
    """项目响应模型"""
    id: int = Field(..., description="项目ID")
    status: str = Field(..., description="项目状态")
    error_message: Optional[str] = Field(None, description="错误信息")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")
    
    class Config:
        from_attributes = True


class ProjectWithDetails(ProjectResponse):
    """带详细信息的项目响应模型"""
    tags: List[str] = Field(default=[], description="项目标签列表")
    tasks_count: int = Field(0, description="任务数量")