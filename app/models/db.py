# -*- coding: utf-8 -*-
"""数据库模型定义

包含项目中使用的所有数据库模型
"""

import os
from peewee import SqliteDatabase, Model, CharField, TextField, DateTimeField, ForeignKeyField, BooleanField, CompositeKey
from datetime import datetime

# 获取当前文件所在目录
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 数据库配置
DATABASE = os.path.join(base_dir, 'simpletask.db')
db = SqliteDatabase(DATABASE)

class BaseModel(Model):
    """数据库模型基类"""
    class Meta:
        database = db

class MirrorSource(BaseModel):
    """镜像源模型"""
    name = CharField(unique=True, max_length=50)
    url = CharField(unique=True, max_length=255)
    description = TextField(null=True)
    is_active = BooleanField(default=False)

class PythonEnv(BaseModel):
    """Python虚拟环境模型"""
    name = CharField(unique=True, max_length=100)
    python_version = CharField(max_length=20, default='3.9.21')
    status = CharField(max_length=20, default='pending')
    path = CharField(max_length=255)
    requirements = TextField(null=True)
    create_time = DateTimeField(default=datetime.now)
    update_time = DateTimeField(default=datetime.now)
    mirror_source = ForeignKeyField(MirrorSource, backref='envs', null=True)

class EnvLog(BaseModel):
    """环境操作日志模型"""
    env = ForeignKeyField(PythonEnv, backref='logs')
    level = CharField(max_length=10, default='INFO')
    message = TextField()
    timestamp = DateTimeField(default=datetime.now)

class PythonVersion(BaseModel):
    """Python版本模型"""
    version = CharField(unique=True, max_length=20)
    status = CharField(max_length=20, default='pending')  # pending, downloading, installing, ready, failed
    download_url = CharField(max_length=255)
    install_path = CharField(max_length=255, null=True)
    is_default = BooleanField(default=False)
    create_time = DateTimeField(default=datetime.now)
    update_time = DateTimeField(default=datetime.now)
    error_message = TextField(null=True)

class ProjectTag(BaseModel):
    """项目标签模型"""
    name = CharField(unique=True, max_length=50)
    create_time = DateTimeField(default=datetime.now)

class Project(BaseModel):
    """项目模型"""
    name = CharField(unique=True, max_length=100)
    description = TextField(null=True)
    work_path = CharField(max_length=255, default='/')
    source_type = CharField(max_length=20, default='zip')  # zip, git
    source_url = TextField(null=True)  # Git仓库地址
    branch = CharField(max_length=50, default='main')  # Git分支
    git_username = CharField(max_length=100, null=True)  # Git用户名
    git_password = TextField(null=True)  # Git密码
    status = CharField(max_length=20, default='pending')  # pending, ready, failed
    error_message = TextField(null=True)
    create_time = DateTimeField(default=datetime.now)
    update_time = DateTimeField(default=datetime.now)

class ProjectToTag(BaseModel):
    """项目和标签的多对多关联模型"""
    project = ForeignKeyField(Project, backref='tags')
    tag = ForeignKeyField(ProjectTag, backref='projects')

    class Meta:
        primary_key = CompositeKey('project', 'tag')