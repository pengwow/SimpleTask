"""镜像源相关的Pydantic模型"""
from typing import Optional
from pydantic import BaseModel, Field


class MirrorSourceBase(BaseModel):
    """镜像源基础模型"""
    name: str = Field(..., max_length=50, description="镜像源名称")
    url: str = Field(..., max_length=255, description="镜像源URL")
    description: Optional[str] = Field(None, description="镜像源描述")
    is_active: bool = Field(False, description="是否激活")


class MirrorSourceCreate(MirrorSourceBase):
    """创建镜像源的请求模型"""
    pass


class MirrorSourceUpdate(BaseModel):
    """更新镜像源的请求模型"""
    name: Optional[str] = Field(None, max_length=50, description="镜像源名称")
    url: Optional[str] = Field(None, max_length=255, description="镜像源URL")
    description: Optional[str] = Field(None, description="镜像源描述")
    is_active: Optional[bool] = Field(None, description="是否激活")


class MirrorSourceResponse(MirrorSourceBase):
    """镜像源响应模型"""
    id: int = Field(..., description="镜像源ID")
    
    class Config:
        from_attributes = True