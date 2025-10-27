#!/usr/bin/env python3
"""Python虚拟环境管理系统FastAPI主入口

提供完整的Python虚拟环境管理、任务管理、日志管理等功能
"""
import os
import sys
import logging
from contextlib import asynccontextmanager

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('python_envs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('python_envs')

# 导入FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 导入数据库配置和模型
from app.db.database import engine, Base

# 导入路由
from app.api.routes import api_router

# 导入nicegui相关模块
from nicegui import ui

# 导入uvicorn用于运行服务
import uvicorn


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("正在初始化数据库...")
    Base.metadata.create_all(bind=engine)
    logger.info("数据库初始化完成")
    
    yield
    
    # 关闭时执行
    logger.info("应用正在关闭...")


# 创建FastAPI应用
app = FastAPI(
    title="Python虚拟环境管理系统",
    description="提供Python虚拟环境管理、任务调度、项目管理等功能的API服务",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该设置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")

# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Python虚拟环境管理系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# 初始化UI - 将NiceGUI与FastAPI应用集成
# 注意：必须在创建FastAPI应用实例后再导入页面模块，以避免命名冲突
from app.dashboard import pages

ui.run_with(
    app,
    mount_path='/gui',
    storage_secret='python_env_manager_secret_key',
)
if __name__ == "__main__":
    logger.info("启动Python虚拟环境管理服务...")
    logger.info("服务将在 http://localhost:5001 启动")
    logger.info("API文档地址: http://localhost:5001/docs")
    logger.info("前端页面: http://localhost:5001/gui")
    logger.info("按 Ctrl+C 停止服务")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5001,
        reload=True
    )