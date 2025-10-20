"""数据库模型定义

包含项目中使用的所有SQLAlchemy数据库模型
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text, Float, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


# 项目和标签的多对多关联表
project_to_tag = Table(
    'project_to_tag',
    Base.metadata,
    Column('project_id', Integer, ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('project_tags.id', ondelete='CASCADE'), primary_key=True)
)


class MirrorSource(Base):
    """镜像源模型"""
    __tablename__ = "mirror_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    url = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False)
    
    # 关系
    envs = relationship("PythonEnv", back_populates="mirror_source")


class PythonEnv(Base):
    """Python虚拟环境模型"""
    __tablename__ = "python_envs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    python_version = Column(String(20), default='3.9.21')
    status = Column(String(20), default='pending')
    path = Column(String(255), nullable=False)
    requirements = Column(Text, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    mirror_source_id = Column(Integer, ForeignKey("mirror_sources.id"), nullable=True)
    
    # 关系
    mirror_source = relationship("MirrorSource", back_populates="envs")
    logs = relationship("EnvLog", back_populates="env", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="python_env")


class EnvLog(Base):
    """环境操作日志模型"""
    __tablename__ = "env_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    env_id = Column(Integer, ForeignKey("python_envs.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(10), default='INFO')
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    env = relationship("PythonEnv", back_populates="logs")


class PythonVersion(Base):
    """Python版本模型"""
    __tablename__ = "python_versions"
    
    id = Column(Integer, primary_key=True, index=True)
    version = Column(String(20), unique=True, nullable=False, index=True)
    status = Column(String(20), default='pending')  # pending, downloading, installing, ready, failed
    download_url = Column(String(255), nullable=False)
    install_path = Column(String(255), nullable=True)
    is_default = Column(Boolean, default=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    error_message = Column(Text, nullable=True)


class ProjectTag(Base):
    """项目标签模型"""
    __tablename__ = "project_tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    projects = relationship("Project", secondary=project_to_tag, back_populates="tags")


class Project(Base):
    """项目模型"""
    __tablename__ = "projects"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    work_path = Column(String(255), default='/')
    source_type = Column(String(20), default='zip')  # zip, git
    source_url = Column(Text, nullable=True)  # Git仓库地址
    branch = Column(String(50), default='main')  # Git分支
    git_username = Column(String(100), nullable=True)  # Git用户名
    git_password = Column(Text, nullable=True)  # Git密码
    status = Column(String(20), default='pending')  # pending, ready, failed
    error_message = Column(Text, nullable=True)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    tags = relationship("ProjectTag", secondary=project_to_tag, back_populates="projects")
    tasks = relationship("Task", back_populates="project")


class Task(Base):
    """任务模型"""
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    python_env_id = Column(Integer, ForeignKey("python_envs.id"), nullable=False)
    command = Column(Text, nullable=False)
    schedule_type = Column(String(20), nullable=False)  # immediate, interval, one-time, cron
    schedule_config = Column(Text, nullable=False)  # JSON格式的调度配置
    max_instances = Column(Integer, default=1)  # 最大并发实例数
    is_active = Column(Boolean, default=False)
    create_time = Column(DateTime(timezone=True), server_default=func.now())
    update_time = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 关系
    project = relationship("Project", back_populates="tasks")
    python_env = relationship("PythonEnv", back_populates="tasks")
    executions = relationship("TaskExecution", back_populates="task", cascade="all, delete-orphan")


class TaskExecution(Base):
    """任务执行记录模型"""
    __tablename__ = "task_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(String(20), nullable=False)  # running, completed, failed
    duration = Column(Float, nullable=True)  # 执行耗时（秒）
    error_message = Column(Text, nullable=True)
    
    # 关系
    task = relationship("Task", back_populates="executions")
    logs = relationship("TaskLog", back_populates="execution", cascade="all, delete-orphan")


class TaskLog(Base):
    """任务执行日志模型"""
    __tablename__ = "task_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("task_executions.id", ondelete="CASCADE"), nullable=False)
    level = Column(String(10), default='INFO')
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    
    # 关系
    execution = relationship("TaskExecution", back_populates="logs")