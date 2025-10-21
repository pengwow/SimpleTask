"""FastAPI路由定义

包含所有RESTful API接口的路由配置
"""
import json
import logging
import threading
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.db import get_db, MirrorSource, PythonEnv, EnvLog, PythonVersion, Project, ProjectTag, Task, TaskExecution, TaskLog
from app.virtual_envs.env_manager import create_python_env
from app.schemas import (
    MirrorSourceCreate, MirrorSourceUpdate, MirrorSourceResponse,
    PythonEnvCreate, PythonEnvUpdate, PythonEnvResponse, PythonEnvWithDetails,
    PythonVersionCreate, PythonVersionResponse, SetDefaultVersion,
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectWithDetails, ProjectTagResponse,
    TaskCreate, TaskUpdate, TaskResponse, TaskWithDetails, TaskExecutionResponse, TaskExecutionWithDetails, TaskActionResponse,
    EnvLogResponse, TaskLogResponse
)

logger = logging.getLogger('python_envs')

# 创建路由器
api_router = APIRouter(
    prefix="",
    tags=["Python虚拟环境管理系统"],
    responses={404: {"description": "Not found"}},
)

# 项目管理相关路由
@api_router.get("/projects", response_model=List[ProjectWithDetails])
async def get_projects(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    db: Session = Depends(get_db)
):
    """获取项目列表
    
    Args:
        skip: 跳过的记录数
        limit: 返回的最大记录数
        db: 数据库会话
        
    Returns:
        项目列表，包含详细信息
    """
    projects = db.query(Project).offset(skip).limit(limit).all()
    result = []
    for project in projects:
        project_with_details = ProjectWithDetails(
            id=project.id,
            name=project.name,
            description=project.description,
            work_path=project.work_path,
            source_type=project.source_type,
            source_url=project.source_url,
            branch=project.branch,
            git_username=project.git_username,
            git_password=project.git_password,
            status=project.status,
            error_message=project.error_message,
            create_time=project.create_time,
            update_time=project.update_time,
            tags=[ProjectTagResponse.from_orm(tag) for tag in project.tags],
            tasks_count=len(project.tasks)
        )
        result.append(project_with_details)
    return result

@api_router.post("/projects", response_model=ProjectResponse)
async def create_project(
    project_data: ProjectCreate,
    db: Session = Depends(get_db)
):
    """创建新项目
    
    Args:
        project_data: 项目创建数据
        db: 数据库会话
        
    Returns:
        创建的项目信息
        
    Raises:
        HTTPException: 当项目名称已存在时
    """
    # 检查项目名称是否已存在
    existing_project = db.query(Project).filter(Project.name == project_data.name).first()
    if existing_project:
        raise HTTPException(status_code=400, detail="项目名称已存在")
    
    # 创建项目
    db_project = Project(**project_data.dict(exclude={'tag_ids'}))
    db_project.status = 'pending'
    
    # 添加标签关联
    if project_data.tag_ids:
        tags = db.query(ProjectTag).filter(ProjectTag.id.in_(project_data.tag_ids)).all()
        db_project.tags = tags
    
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    # 这里应该添加异步创建项目的逻辑
    # 暂时直接设置为ready状态
    db_project.status = 'ready'
    db.commit()
    
    return db_project

@api_router.get("/projects/{project_id}", response_model=ProjectWithDetails)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """获取项目详情
    
    Args:
        project_id: 项目ID
        db: 数据库会话
        
    Returns:
        项目详情信息
        
    Raises:
        HTTPException: 当项目不存在时
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    return ProjectWithDetails(
        id=project.id,
        name=project.name,
        description=project.description,
        work_path=project.work_path,
        source_type=project.source_type,
        source_url=project.source_url,
        branch=project.branch,
        git_username=project.git_username,
        git_password=project.git_password,
        status=project.status,
        error_message=project.error_message,
        create_time=project.create_time,
        update_time=project.update_time,
        tags=[ProjectTagResponse.from_orm(tag) for tag in project.tags],
        tasks_count=len(project.tasks)
    )

@api_router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: Session = Depends(get_db)
):
    """更新项目信息
    
    Args:
        project_id: 项目ID
        project_data: 项目更新数据
        db: 数据库会话
        
    Returns:
        更新后的项目信息
        
    Raises:
        HTTPException: 当项目不存在或名称冲突时
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查名称是否与其他项目冲突
    if project_data.name and project_data.name != project.name:
        existing_project = db.query(Project).filter(Project.name == project_data.name).first()
        if existing_project:
            raise HTTPException(status_code=400, detail="项目名称已存在")
    
    # 更新项目信息
    update_data = project_data.dict(exclude_unset=True)
    tag_ids = update_data.pop('tag_ids', None)
    
    for field, value in update_data.items():
        setattr(project, field, value)
    
    # 更新标签关联
    if tag_ids is not None:
        tags = db.query(ProjectTag).filter(ProjectTag.id.in_(tag_ids)).all()
        project.tags = tags
    
    project.update_time = datetime.now()
    db.commit()
    db.refresh(project)
    
    return project

@api_router.delete("/projects/{project_id}", response_model=dict)
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db)
):
    """删除项目
    
    Args:
        project_id: 项目ID
        db: 数据库会话
        
    Returns:
        删除成功信息
        
    Raises:
        HTTPException: 当项目不存在时
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 检查是否有相关任务
    if project.tasks:
        raise HTTPException(status_code=400, detail="项目下还有任务，无法删除")
    
    db.delete(project)
    db.commit()
    
    return {"message": "项目删除成功"}

@api_router.post("/projects/{project_id}/upload")
async def upload_project_file(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """上传项目ZIP文件
    
    Args:
        project_id: 项目ID
        file: 上传的ZIP文件
        db: 数据库会话
        
    Returns:
        上传成功信息
        
    Raises:
        HTTPException: 当项目不存在或文件类型错误时
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="只能上传ZIP文件")
    
    # 这里应该添加文件保存和项目解压的逻辑
    # 暂时返回成功信息
    return {"message": "文件上传成功"}

@api_router.get("/projects/{project_id}/files/{file_path:path}")
async def get_project_file(
    project_id: int,
    file_path: str,
    db: Session = Depends(get_db)
):
    """获取项目文件内容
    
    Args:
        project_id: 项目ID
        file_path: 文件路径
        db: 数据库会话
        
    Returns:
        文件内容
        
    Raises:
        HTTPException: 当项目或文件不存在时
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")
    
    # 这里应该添加实际读取文件的逻辑
    # 暂时返回模拟数据
    return {"content": "文件内容示例", "file_path": file_path}

@api_router.get("/project_tags", response_model=List[ProjectTagResponse])
async def get_project_tags(
    db: Session = Depends(get_db)
):
    """获取所有项目标签
    
    Args:
        db: 数据库会话
        
    Returns:
        标签列表
    """
    tags = db.query(ProjectTag).all()
    return tags

# API接口定义 - 虚拟环境管理
@api_router.get("/envs", response_model=List[PythonEnvResponse])
async def get_envs(
    db: Session = Depends(get_db)
):
    """获取所有虚拟环境列表
    
    Args:
        db: 数据库会话
        
    Returns:
        虚拟环境列表
    """
    envs = db.query(PythonEnv).order_by(PythonEnv.create_time.desc()).all()
    return envs

@api_router.get("/envs/{env_id}", response_model=PythonEnvWithDetails)
async def get_env(
    env_id: int,
    db: Session = Depends(get_db)
):
    """获取单个虚拟环境详情
    
    Args:
        env_id: 环境ID
        db: 数据库会话
        
    Returns:
        环境详情
        
    Raises:
        HTTPException: 当环境不存在时
    """
    env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="虚拟环境不存在")
    return env

@api_router.post("/envs", response_model=PythonEnvResponse)
async def create_env(
    env_data: PythonEnvCreate,
    db: Session = Depends(get_db)
):
    """创建新的Python虚拟环境
    
    Args:
        env_data: 环境创建数据
        db: 数据库会话
        
    Returns:
        创建的环境信息
        
    Raises:
        HTTPException: 当环境名称已存在时
    """
    # 检查环境名称是否已存在
    existing_env = db.query(PythonEnv).filter(PythonEnv.name == env_data.name).first()
    if existing_env:
        raise HTTPException(status_code=400, detail="环境名称已存在")
    
    # 创建环境记录
    db_env = PythonEnv(
        name=env_data.name,
        python_version=env_data.python_version,
        requirements=env_data.requirements,
        path='',
        status='pending'
    )
    
    db.add(db_env)
    db.commit()
    db.refresh(db_env)
    
    # 异步创建虚拟环境
    # 启动一个线程来执行实际的环境创建操作
    thread = threading.Thread(target=create_python_env, args=(db_env.id,), daemon=True)
    thread.start()
    
    return db_env

@api_router.put("/envs/{env_id}", response_model=PythonEnvResponse)
async def update_env(
    env_id: int,
    env_data: PythonEnvUpdate,
    db: Session = Depends(get_db)
):
    """更新Python虚拟环境
    
    Args:
        env_id: 环境ID
        env_data: 环境更新数据
        db: 数据库会话
        
    Returns:
        更新后的环境信息
        
    Raises:
        HTTPException: 当环境不存在或状态不允许更新时
    """
    env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    # 只有ready状态的环境才能更新
    if env.status != 'ready':
        raise HTTPException(status_code=400, detail="只有就绪状态的环境才能更新")
    
    # 更新环境信息
    update_data = env_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(env, field, value)
    
    env.update_time = datetime.now()
    db.commit()
    db.refresh(env)
    
    # 这里应该添加异步安装依赖包的逻辑
    # 暂时直接返回更新后的环境信息
    
    return env

@api_router.delete("/envs/{env_id}", response_model=dict)
async def delete_env(
    env_id: int,
    db: Session = Depends(get_db)
):
    """删除Python虚拟环境
    
    Args:
        env_id: 环境ID
        db: 数据库会话
        
    Returns:
        删除成功信息
        
    Raises:
        HTTPException: 当环境不存在时
    """
    env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    # 检查是否有相关任务在使用此环境
    # 这里应该添加实际检查逻辑
    
    # 这里应该添加实际删除虚拟环境文件的逻辑
    
    db.delete(env)
    db.commit()
    
    return {"message": "环境删除成功"}

@api_router.get("/envs/{env_id}/logs", response_model=List[EnvLogResponse])
async def get_env_logs(
    env_id: int,
    db: Session = Depends(get_db)
):
    """获取环境操作日志
    
    Args:
        env_id: 环境ID
        db: 数据库会话
        
    Returns:
        日志列表
        
    Raises:
        HTTPException: 当环境不存在时
    """
    # 检查环境是否存在
    env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
    if not env:
        raise HTTPException(status_code=404, detail="环境不存在")
    
    # 获取环境日志
    logs = db.query(EnvLog).filter(
        EnvLog.env_id == env_id
    ).order_by(EnvLog.timestamp.desc()).limit(100).all()
    
    return logs

@api_router.get("/envs/{env_id}/log_stream")
async def log_stream(env_id: int, db: Session = Depends(get_db)):
    """实时获取环境的安装日志流
    
    Args:
        env_id: 环境ID
        db: 数据库会话
        
    Returns:
        实时日志流
    """
    import asyncio
    from fastapi.responses import StreamingResponse
    
    # FastAPI中实现SSE的方式
    async def event_generator():
        # 首先发送所有历史日志
        try:
            logs = db.query(EnvLog).filter(EnvLog.env_id == env_id).order_by(EnvLog.timestamp).all()
            for log in logs:
                timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                yield f'data: [{timestamp}] [{log.level}] {log.message}\n\n'
        except Exception as e:
            logger.error(f"获取历史日志失败: {str(e)}")
            yield f'data: [ERROR] 获取历史日志失败: {str(e)}\n\n'
        
        # 这里应该添加实时日志队列逻辑
        # 暂时返回一些模拟数据
        for i in range(5):
            data = {
                "message": f"实时日志消息 {i}",
                "type": "info",
                "timestamp": datetime.now().isoformat()
            }
            yield f"data: {json.dumps(data)}\n\n"
            await asyncio.sleep(1)
        
        # 发送结束信号
        yield 'data: [STREAM_END]\n\n'
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# API接口定义 - 镜像源管理
@api_router.get("/mirrors", response_model=List[MirrorSourceResponse])
async def get_mirrors(
    db: Session = Depends(get_db)
):
    """获取所有镜像源列表
    
    Args:
        db: 数据库会话
        
    Returns:
        镜像源列表
    """
    mirrors = db.query(MirrorSource).all()
    return mirrors

@api_router.get("/mirrors/{mirror_id}", response_model=MirrorSourceResponse)
async def get_mirror(
    mirror_id: int,
    db: Session = Depends(get_db)
):
    """获取单个镜像源信息
    
    Args:
        mirror_id: 镜像源ID
        db: 数据库会话
        
    Returns:
        镜像源详情
        
    Raises:
        HTTPException: 当镜像源不存在时
    """
    mirror = db.query(MirrorSource).filter(MirrorSource.id == mirror_id).first()
    if not mirror:
        raise HTTPException(status_code=404, detail="镜像源不存在")
    return mirror

@api_router.post("/mirrors", response_model=MirrorSourceResponse)
async def create_mirror(
    mirror_data: MirrorSourceCreate,
    db: Session = Depends(get_db)
):
    """创建新的镜像源
    
    Args:
        mirror_data: 镜像源创建数据
        db: 数据库会话
        
    Returns:
        创建的镜像源信息
        
    Raises:
        HTTPException: 当镜像源名称或URL已存在时
    """
    # 检查名称是否已存在
    if db.query(MirrorSource).filter(MirrorSource.name == mirror_data.name).first():
        raise HTTPException(status_code=400, detail="镜像源名称已存在")
    
    # 检查URL是否已存在
    if db.query(MirrorSource).filter(MirrorSource.url == mirror_data.url).first():
        raise HTTPException(status_code=400, detail="镜像源URL已存在")
    
    # 创建镜像源
    new_mirror = MirrorSource(**mirror_data.dict())
    db.add(new_mirror)
    db.commit()
    db.refresh(new_mirror)
    
    return new_mirror

@api_router.put("/mirrors/{mirror_id}", response_model=MirrorSourceResponse)
async def update_mirror(
    mirror_id: int,
    mirror_data: MirrorSourceUpdate,
    db: Session = Depends(get_db)
):
    """更新镜像源信息
    
    Args:
        mirror_id: 镜像源ID
        mirror_data: 镜像源更新数据
        db: 数据库会话
        
    Returns:
        更新后的镜像源信息
        
    Raises:
        HTTPException: 当镜像源不存在时
    """
    mirror = db.query(MirrorSource).filter(MirrorSource.id == mirror_id).first()
    if not mirror:
        raise HTTPException(status_code=404, detail="镜像源不存在")
    
    # 更新字段
    update_data = mirror_data.dict(exclude_unset=True)
    
    # 检查名称冲突
    if 'name' in update_data and update_data['name'] != mirror.name:
        if db.query(MirrorSource).filter(MirrorSource.name == update_data['name']).first():
            raise HTTPException(status_code=400, detail="镜像源名称已存在")
    
    # 检查URL冲突
    if 'url' in update_data and update_data['url'] != mirror.url:
        if db.query(MirrorSource).filter(MirrorSource.url == update_data['url']).first():
            raise HTTPException(status_code=400, detail="镜像源URL已存在")
    
    # 处理激活状态
    if 'is_active' in update_data and update_data['is_active']:
        # 先取消其他所有镜像源的激活状态
        db.query(MirrorSource).update({MirrorSource.is_active: False})
        mirror.is_active = True
    elif 'is_active' in update_data:
        mirror.is_active = update_data['is_active']
    
    # 更新其他字段
    for field, value in update_data.items():
        if field != 'is_active':  # is_active已经单独处理
            setattr(mirror, field, value)
    
    db.commit()
    db.refresh(mirror)
    
    return mirror

@api_router.delete("/mirrors/{mirror_id}", response_model=dict)
async def delete_mirror(
    mirror_id: int,
    db: Session = Depends(get_db)
):
    """删除镜像源
    
    Args:
        mirror_id: 镜像源ID
        db: 数据库会话
        
    Returns:
        删除成功信息
        
    Raises:
        HTTPException: 当镜像源不存在或正在使用时
    """
    mirror = db.query(MirrorSource).filter(MirrorSource.id == mirror_id).first()
    if not mirror:
        raise HTTPException(status_code=404, detail="镜像源不存在")
    
    # 不能删除最后一个镜像源
    if db.query(MirrorSource).count() <= 1:
        raise HTTPException(status_code=400, detail="至少保留一个镜像源")
    
    # 如果删除的是活跃镜像源，自动激活第一个可用的镜像源
    if mirror.is_active:
        first_mirror = db.query(MirrorSource).filter(MirrorSource.id != mirror_id).first()
        if first_mirror:
            first_mirror.is_active = True
    
    # 检查是否有虚拟环境正在使用此镜像源
    env_count = db.query(PythonEnv).filter(PythonEnv.mirror_source_id == mirror_id).count()
    if env_count > 0:
        raise HTTPException(status_code=400, detail=f"该镜像源正在被{env_count}个虚拟环境使用，无法删除")
    
    db.delete(mirror)
    db.commit()
    
    return {"message": "镜像源删除成功"}

@api_router.get("/mirrors/active", response_model=MirrorSourceResponse)
async def get_active_mirror_api(
    db: Session = Depends(get_db)
):
    """获取当前活跃的镜像源
    
    Args:
        db: 数据库会话
        
    Returns:
        活跃镜像源信息
        
    Raises:
        HTTPException: 当没有活跃的镜像源时
    """
    mirror = db.query(MirrorSource).filter(MirrorSource.is_active == True).first()
    if not mirror:
        raise HTTPException(status_code=404, detail="没有活跃的镜像源")
    return mirror

# FastAPI中数据库连接通过依赖注入管理，不需要Flask的before_request和after_request钩子
# 数据库会话通过get_db依赖项自动管理打开和关闭

# API接口定义 - Python版本管理
@api_router.get("/python_versions", response_model=List[PythonVersionResponse])
async def get_python_versions(
    db: Session = Depends(get_db)
):
    """获取所有Python版本列表
    
    Args:
        db: 数据库会话
        
    Returns:
        Python版本列表
    """
    versions = db.query(PythonVersion).order_by(PythonVersion.version.desc()).all()
    return versions

@api_router.get("/python_versions/<int:version_id>", response_model=PythonVersionResponse)
async def get_python_version(
    version_id: int,
    db: Session = Depends(get_db)
):
    """获取单个Python版本详情
    
    Args:
        version_id: 版本ID
        db: 数据库会话
        
    Returns:
        Python版本详情
        
    Raises:
        HTTPException: 当版本不存在时
    """
    version = db.query(PythonVersion).filter(PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python版本不存在")
    return version

@api_router.post("/python_versions", response_model=PythonVersionResponse)
async def add_python_version(
    python_version: PythonVersionCreate,
    db: Session = Depends(get_db)
):
    """添加Python版本
    
    Args:
        python_version: Python版本创建数据
        db: 数据库会话
        
    Returns:
        创建的Python版本信息
        
    Raises:
        HTTPException: 当参数无效或版本已存在时
    """
    # 验证下载地址格式
    if not python_version.download_url.endswith('.tar.xz'):
        raise HTTPException(status_code=400, detail='请下载.tar.xz格式的安装包')
    
    # 检查版本是否已存在
    if db.query(PythonVersion).filter(PythonVersion.version == python_version.version).first():
        raise HTTPException(status_code=400, detail='Python版本已存在')
        
    # 创建版本记录
    db_version = PythonVersion(
        version=python_version.version,
        status='pending',
        download_url=python_version.download_url,
        install_path='',
        is_default=False
    )
    db.add(db_version)
    db.commit()
    db.refresh(db_version)
    
    # 初始化日志队列
    with python_version_log_queues_lock:
        python_version_log_queues[db_version.id] = Queue(maxsize=1000)
    
    # 启动线程下载和安装Python版本
    thread = threading.Thread(
        target=PythonVersionManager._download_and_install_python,
        args=(db_version.id, python_version.version, python_version.download_url)
    )
    thread.daemon = True
    thread.start()
    
    return db_version

@api_router.post("/python_versions/<int:version_id>/set_default", response_model=dict)
async def set_default_python_version(
    version_id: int,
    db: Session = Depends(get_db)
):
    """设置默认Python版本
    
    Args:
        version_id: 版本ID
        db: 数据库会话
        
    Returns:
        设置结果消息
        
    Raises:
        HTTPException: 当版本不存在或状态不正确时
    """
    version = db.query(PythonVersion).filter(PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python版本不存在")
    
    # 检查版本是否已安装完成
    if version.status != 'ready':
        raise HTTPException(status_code=400, detail='只有已安装完成的Python版本才能设为默认')
    
    # 设置默认版本
    PythonVersionManager.set_default_version(version_id)
    
    return {"message": "默认Python版本设置成功"}

@api_router.delete("/python_versions/<int:version_id>", response_model=dict)
async def delete_python_version(
    version_id: int,
    db: Session = Depends(get_db)
):
    """删除Python版本
    
    Args:
        version_id: 版本ID
        db: 数据库会话
        
    Returns:
        删除结果消息
        
    Raises:
        HTTPException: 当版本不存在或无法删除时
    """
    version = db.query(PythonVersion).filter(PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python版本不存在")
    
    # 不能删除默认版本
    if version.is_default:
        raise HTTPException(status_code=400, detail='不能删除默认Python版本，请先设置其他版本为默认')
    
    # 删除版本
    PythonVersionManager.delete_version(version_id)
    
    # 清理日志队列
    with python_version_log_queues_lock:
        if version_id in python_version_log_queues:
            del python_version_log_queues[version_id]
    
    return {"message": "Python版本删除成功"}

@api_router.get("/python_versions/<int:version_id>/log_stream")
async def python_version_log_stream(
    version_id: int,
    db: Session = Depends(get_db)
):
    """实时获取Python版本安装日志流
    
    Args:
        version_id: 版本ID
        db: 数据库会话
        
    Returns:
        StreamingResponse: 日志事件流
    """
    # 检查版本是否存在
    version = db.query(PythonVersion).filter(PythonVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Python版本不存在")
    
    async def event_stream():
        # 初始化日志队列
        with python_version_log_queues_lock:
            if version_id not in python_version_log_queues:
                python_version_log_queues[version_id] = Queue(maxsize=1000)
        
        # 实时发送新日志
        while True:
            try:
                with python_version_log_queues_lock:
                    if version_id not in python_version_log_queues:
                        break
                    queue_ref = python_version_log_queues[version_id]
                
                try:
                    log = queue_ref.get(timeout=1)
                    yield f'data: {log}\n\n'
                except Empty:
                    # 检查版本是否已完成安装
                    try:
                        version = db.query(PythonVersion).filter(PythonVersion.id == version_id).first()
                        if version and version.status in ['ready', 'failed']:
                            # 检查是否还有日志需要发送
                            if queue_ref.empty():
                                await asyncio.sleep(1)  # 等待1秒确保所有日志都已处理
                                break
                    except Exception as e:
                        logger.error(f"检查Python版本状态出错: {str(e)}")
                        break
                    continue
                except Full:
                    continue
            except GeneratorExit:
                break
            except Exception as e:
                logger.error(f"日志流出错: {str(e)}")
                break
            
            await asyncio.sleep(0.1)  # 避免CPU占用过高
        
        # 发送结束信号
        yield 'data: [STREAM_END]\n\n'
    
    return StreamingResponse(event_stream(), media_type='text/event-stream')

# 任务管理相关的路由
@api_router.get("/tasks", response_model=List[TaskWithDetails])
async def get_tasks(
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    search: str = Query("", description="搜索关键词"),
    project_id: Optional[int] = Query(None, description="项目ID过滤"),
    python_env_id: Optional[int] = Query(None, description="Python虚拟环境ID过滤"),
    is_active: Optional[bool] = Query(None, description="任务状态过滤"),
    db: Session = Depends(get_db)
):
    """获取任务列表
    
    Args:
        page: 页码，默认为1
        per_page: 每页数量，默认为10
        search: 搜索关键词
        project_id: 项目ID过滤
        python_env_id: Python虚拟环境ID过滤
        is_active: 任务状态过滤
        db: 数据库会话
        
    Returns:
        任务列表和分页信息
    """
    # 构建查询
    query = db.query(Task)
    
    # 应用过滤条件
    if project_id is not None:
        query = query.filter(Task.project_id == project_id)
    
    if python_env_id is not None:
        query = query.filter(Task.python_env_id == python_env_id)
    
    if is_active is not None:
        query = query.filter(Task.is_active == is_active)
    
    if search:
        search_filter = (Task.name.contains(search)) | (Task.description.contains(search))
        query = query.filter(search_filter)
    
    # 获取总数
    total = query.count()
    
    # 应用分页
    offset = (page - 1) * per_page
    tasks = query.order_by(Task.created_at.desc()).offset(offset).limit(per_page).all()
    
    # 构建响应
    return {
        "success": True,
        "data": tasks,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@api_router.post("/tasks", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    """创建新任务
    
    Args:
        task_data: 任务创建数据
        db: 数据库会话
        
    Returns:
        创建的任务信息
        
    Raises:
        HTTPException: 当参数无效或创建失败时
    """
    # 验证Python虚拟环境是否存在
    if task_data.python_env_id:
        env = db.query(PythonEnv).filter(PythonEnv.id == task_data.python_env_id).first()
        if not env:
            raise HTTPException(status_code=404, detail="Python虚拟环境不存在")
    
    # 验证项目是否存在（如果提供了project_id）
    if task_data.project_id:
        project = db.query(Project).filter(Project.id == task_data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
    
    # 创建任务记录
    task = Task(
        name=task_data.name,
        description=task_data.description,
        project_id=task_data.project_id,
        python_env_id=task_data.python_env_id,
        command=task_data.command,
        schedule_type=task_data.schedule_type,
        schedule_config=task_data.schedule_config,
        max_instances=task_data.max_instances or 1,
        is_active=True
    )
    
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # 如果是立即执行的任务，启动任务
    if task.schedule_type == 'immediate':
        try:
            task_manager.start_task(task.id)
        except Exception as e:
            logger.error(f"启动任务失败: {str(e)}")
            # 不影响任务创建，只记录错误
    
    return task

@api_router.get("/tasks/<int:task_id>", response_model=TaskResponse)
async def get_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取任务详情
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        任务详情
        
    Raises:
        HTTPException: 当任务不存在时
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@api_router.put("/tasks/<int:task_id>", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db)
):
    """更新任务信息
    
    Args:
        task_id: 任务ID
        task_data: 任务更新数据
        db: 数据库会话
        
    Returns:
        更新后的任务信息
        
        HTTPException: 当任务不存在或参数无效时
    """
    # 获取任务
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 验证Python虚拟环境是否存在（如果更新了python_env_id）
    if task_data.python_env_id is not None:
        env = db.query(PythonEnv).filter(PythonEnv.id == task_data.python_env_id).first()
        if not env:
            raise HTTPException(status_code=404, detail="Python虚拟环境不存在")
    
    # 验证项目是否存在（如果更新了project_id）
    if task_data.project_id is not None:
        project = db.query(Project).filter(Project.id == task_data.project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="项目不存在")
    
    # 更新任务字段
    update_data = task_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(task, field, value)
    
    # 如果任务被重新激活，需要重新调度
    if 'is_active' in update_data and update_data['is_active'] and task.schedule_type != 'immediate':
        task_manager.schedule_task(task.id)
    
    db.commit()
    db.refresh(task)
    return task

@api_router.delete("/tasks/<int:task_id>")
async def delete_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """删除任务
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        操作结果
        
        HTTPException: 当任务不存在时
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查是否有正在运行的任务实例
    running_instances = db.query(TaskInstance).filter(
        TaskInstance.task_id == task_id,
        TaskInstance.status.in_(["running", "queued"])
    ).count()
    
    if running_instances > 0:
        raise HTTPException(status_code=400, detail="有正在运行的任务实例，无法删除")
    
    # 删除相关的任务实例和日志
    db.query(TaskInstance).filter(TaskInstance.task_id == task_id).delete()
    
    # 删除任务
    db.delete(task)
    db.commit()
    
    return {"success": True, "message": "任务删除成功"}

@api_router.post("/tasks/<int:task_id>/start", response_model=TaskResponse)
async def start_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """启动任务
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        任务信息
        
    Raises:
        HTTPException: 当任务不存在或无法启动时
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 检查任务是否处于可启动状态
    if not task.is_active:
        raise HTTPException(status_code=400, detail="任务未激活")
    
    # 检查是否达到最大实例数
    running_instances = db.query(TaskInstance).filter(
        TaskInstance.task_id == task_id,
        TaskInstance.status.in_(['running', 'queued'])
    ).count()
    
    if running_instances >= task.max_instances:
        raise HTTPException(status_code=400, detail="已达到最大并发实例数")
    
    # 创建任务实例并启动
    try:
        # 更新任务状态
        task.last_run_time = datetime.utcnow()
        db.commit()
        
        # 调用任务管理模块启动任务
        result = task_manager.start_task(task_id)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])
        
        db.refresh(task)
        return task
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f'启动任务失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f"启动任务失败: {str(e)}")

@api_router.post("/tasks/<int:task_id>/pause", response_model=TaskResponse)
async def pause_task(
    task_id: int,
    db: Session = Depends(get_db)
):
    """暂停任务
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        任务信息
        
    Raises:
        HTTPException: 当任务不存在或无法暂停时
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 更新任务状态为未激活
    task.is_active = False
    
    # 尝试取消所有排队的任务实例
    db.query(TaskInstance).filter(
        TaskInstance.task_id == task_id,
        TaskInstance.status == 'queued'
    ).update({TaskInstance.status: 'cancelled'})
    
    try:
        db.commit()
        
        # 调用任务管理模块暂停任务调度
        result = task_manager.pause_task(task_id)
        
        if not result['success']:
            logger.warning(f'任务管理模块暂停任务失败: {result.get("message", "未知错误")}')
        
        db.refresh(task)
        return task
    except Exception as e:
        db.rollback()
        logger.error(f'暂停任务失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f"暂停任务失败: {str(e)}")

@api_router.get("/tasks/{task_id}/executions", response_model=List[TaskExecutionWithDetails])
async def get_task_executions(
    task_id: int,
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(10, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="执行状态过滤"),
    db: Session = Depends(get_db)
):
    """获取任务执行历史记录
    
    Args:
        task_id: 任务ID
        page: 页码
        per_page: 每页数量
        status: 执行状态过滤
        db: 数据库会话
        
    Returns:
        执行历史记录列表
        
    Raises:
        HTTPException: 当任务不存在时
    """
    # 验证任务是否存在
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 查询任务执行记录
    query = db.query(TaskExecution).filter(TaskExecution.task_id == task_id)
    
    # 应用状态过滤
    if status:
        query = query.filter(TaskExecution.status == status)
    
    # 获取总数
    total = query.count()
    
    # 分页
    executions = query.order_by(TaskExecution.id.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "executions": executions,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page
    }

@api_router.get("/executions/{execution_id}/logs", response_model=TaskLogResponse)
async def get_execution_logs(
    execution_id: int,
    page: int = Query(1, ge=1, description="页码"),
    per_page: int = Query(50, ge=1, le=100, description="每页数量"),
    level: Optional[str] = Query(None, description="日志级别过滤"),
    search: str = Query("", description="关键词搜索"),
    db: Session = Depends(get_db)
):
    """获取任务执行日志
    
    Args:
        execution_id: 执行ID
        page: 页码
        per_page: 每页数量
        level: 日志级别过滤
        search: 关键词搜索
        db: 数据库会话
        
    Returns:
        执行日志信息
        
    Raises:
        HTTPException: 当执行记录不存在时
    """
    # 查询执行记录
    execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 构建查询
    query = db.query(TaskLog).filter(TaskLog.execution_id == execution_id)
    
    # 应用过滤条件
    if level:
        query = query.filter(TaskLog.level == level)
    
    if search:
        query = query.filter(TaskLog.message.contains(search))
    
    # 获取总数
    total = query.count()
    
    # 分页
    logs = query.order_by(TaskLog.timestamp.desc()).offset((page - 1) * per_page).limit(per_page).all()
    
    return {
        "success": True,
        "execution_id": execution_id,
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page
    }

@api_router.post("/executions/<int:execution_id>/terminate")
async def terminate_execution(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """终止任务执行
    
    Args:
        execution_id: 执行ID
        db: 数据库会话
        
    Returns:
        操作结果
        
    Raises:
        HTTPException: 当执行记录不存在或无法终止时
    """
    # 查询执行记录
    execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 检查执行状态
    if execution.status not in ['running', 'queued']:
        raise HTTPException(status_code=400, detail="该执行已结束或已被终止")
    
    try:
        # 调用任务管理模块终止执行
        result = task_manager.terminate_execution(execution_id)
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result['message'])
        
        # 更新执行状态
        execution.status = 'cancelled'
        execution.end_time = datetime.utcnow()
        db.commit()
        
        return {"success": True, "message": "任务执行已成功终止"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f'终止任务执行失败: {str(e)}')
        raise HTTPException(status_code=500, detail=f"终止任务执行失败: {str(e)}")

@api_router.get("/tasks/{task_id}/running_instances", response_model=dict)
async def get_task_running_instances(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取任务运行实例
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        运行实例列表
        
    Raises:
        HTTPException: 当任务不存在时
    """
    # 验证任务是否存在
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 查询运行中的实例
    running_instances = db.query(TaskExecution).filter(
        TaskExecution.task_id == task_id,
        TaskExecution.status.in_(['running', 'queued'])
    ).order_by(TaskExecution.created_at.desc()).all()
    
    return {
        "success": True,
        "task_id": task_id,
        "instances": [
            {
                "id": instance.id,
                "status": instance.status,
                "created_at": instance.created_at,
                "started_at": instance.started_at
            } for instance in running_instances
        ],
        "count": len(running_instances)
    }

@api_router.get("/tasks/<int:task_id>/stats", response_model=dict)
async def get_task_stats(
    task_id: int,
    db: Session = Depends(get_db)
):
    """获取任务统计信息
    
    Args:
        task_id: 任务ID
        db: 数据库会话
        
    Returns:
        任务统计信息
        
    Raises:
        HTTPException: 当任务不存在时
    """
    # 验证任务是否存在
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    # 计算统计信息
    executions = db.query(TaskExecution).filter(TaskExecution.task_id == task_id)
    
    # 执行总数
    total_executions = executions.count()
    
    # 成功执行数
    successful_executions = executions.filter(TaskExecution.status == 'success').count()
    
    # 失败执行数
    failed_executions = executions.filter(TaskExecution.status == 'failed').count()
    
    # 运行中执行数
    running_executions = executions.filter(TaskExecution.status == 'running').count()
    
    # 最近执行记录
    latest_execution = executions.order_by(TaskExecution.created_at.desc()).first()
    
    # 成功率
    success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
    
    return {
        "success": True,
        "task_id": task_id,
        "total_executions": total_executions,
        "successful_executions": successful_executions,
        "failed_executions": failed_executions,
        "running_executions": running_executions,
        "success_rate": round(success_rate, 2),
        "latest_execution": {
            "id": latest_execution.id,
            "status": latest_execution.status,
            "created_at": latest_execution.created_at,
            "started_at": latest_execution.started_at,
            "end_time": latest_execution.end_time
        } if latest_execution else None
    }

@api_router.get("/tasks/<int:task_id>/executions/<int:execution_id>/realtime_logs")
async def get_realtime_logs(
    task_id: int,
    execution_id: int,
    db: Session = Depends(get_db)
):
    """获取任务执行的实时日志
    
    Args:
        task_id: 任务ID
        execution_id: 执行ID
        db: 数据库会话
        
    Returns:
        实时日志流
        
    Raises:
        HTTPException: 当任务或执行记录不存在时
    """
    # 验证任务和执行记录
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    execution = db.query(TaskExecution).filter(TaskExecution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="执行记录不存在")
    
    # 生成日志流
    async def log_stream():
        last_log_time = datetime.utcnow()
        # 持续发送日志，直到客户端断开连接或执行结束
        while True:
            try:
                # 获取新的日志
                new_logs = db.query(TaskLog).filter(
                    TaskLog.execution_id == execution_id,
                    TaskLog.timestamp > last_log_time
                ).order_by(TaskLog.timestamp).all()
                
                if new_logs:
                    for log in new_logs:
                        log_data = {
                            "id": log.id,
                            "timestamp": log.timestamp.isoformat(),
                            "level": log.level,
                            "message": log.message
                        }
                        yield f'data: {json.dumps(log_data)}\n\n'
                        last_log_time = log.timestamp
                
                # 刷新数据库会话以获取最新数据
                db.refresh(execution)
                
                # 检查执行是否结束
                if execution.status in ['success', 'failed', 'cancelled']:
                    yield 'data: {"event": "end", "message": "执行已结束"}\n\n'
                    break
                
                # 避免CPU占用过高
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f'发送实时日志失败: {str(e)}')
                yield f'data: {{"event": "error", "message": "{str(e)}"}}\n\n'
                await asyncio.sleep(1)
    
    return StreamingResponse(log_stream(), media_type='text/event-stream')

# 数据库连接管理
# 在FastAPI中，数据库连接通过依赖项(get_db)来管理，不再需要before_request和after_request钩子

# 如果你需要全局的请求处理，可以使用FastAPI的中间件
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# 示例：数据库会话中间件（如果需要）
class DatabaseSessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 注意：这里只是示例，实际的数据库连接应该通过依赖项管理
        # 因为我们已经使用了get_db依赖项，这个中间件可能是多余的
        response = await call_next(request)
        return response