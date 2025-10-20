"""Python版本相关的Pydantic模型"""
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PythonVersionBase(BaseModel):
    """Python版本基础模型"""
    version: str = Field(..., max_length=20, description="Python版本号")
    download_url: str = Field(..., max_length=255, description="下载URL")


class PythonVersionCreate(PythonVersionBase):
    """创建Python版本的请求模型"""
    pass


class PythonVersionResponse(PythonVersionBase):
    """Python版本响应模型"""
    id: int = Field(..., description="版本ID")
    status: str = Field(..., description="版本状态")
    install_path: Optional[str] = Field(None, description="安装路径")
    is_default: bool = Field(..., description="是否为默认版本")
    create_time: datetime = Field(..., description="创建时间")
    update_time: datetime = Field(..., description="更新时间")
    error_message: Optional[str] = Field(None, description="错误信息")
    
    class Config:
        from_attributes = True


class SetDefaultVersion(BaseModel):
    """设置默认版本的响应模型"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    version_id: int = Field(..., description="版本ID")