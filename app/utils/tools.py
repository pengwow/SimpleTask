# -*- coding: utf-8 -*-
"""工具函数模块

包含项目中使用的各种工具函数
"""

import os
import sys
import time
import uuid
import logging
import threading
from datetime import datetime
from queue import Queue, Empty, Full

# 导入数据库模型
from app.models.db import db, MirrorSource, PythonEnv, EnvLog

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

# 虚拟环境根目录
ENV_ROOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'python_envs')

# 确保目录存在
def ensure_dir_exists(dir_path):
    """确保指定的目录存在，如果不存在则创建
    
    参数:
        dir_path: 目录路径
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# 确保虚拟环境根目录存在
# ensure_dir_exists(ENV_ROOT_DIR)

# 日志队列锁和队列字典
log_queues_lock = threading.Lock()
log_queues = {}

# 获取当前活跃的镜像源
def get_active_mirror():
    """获取当前活跃的镜像源
    
    返回:
        MirrorSource: 活跃的镜像源对象
    """
    try:
        return MirrorSource.get(MirrorSource.is_active == True)
    except MirrorSource.DoesNotExist:
        # 如果没有活跃的镜像源，返回阿里云作为默认
        try:
            return MirrorSource.get(MirrorSource.name == 'aliyun')
        except MirrorSource.DoesNotExist:
            return None

# 记录环境日志
def log_env(env_id, message, level='INFO'):
    """记录环境操作日志
    
    参数:
        env_id: 环境ID
        message: 日志消息
        level: 日志级别
    """
    try:
        env = PythonEnv.get_by_id(env_id)
        # 保存到数据库
        EnvLog.create(env=env, level=level, message=message)
        
        # 发送到实时日志队列
        with log_queues_lock:
            if env_id in log_queues:
                try:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                    log_queues[env_id].put(f'[{timestamp}] [{level}] {message}\n')
                except Full:
                    pass
    except Exception as e:
        logger.error(f"记录日志失败: {str(e)}")

# 安装依赖包
def install_requirements(env_id, env_path, requirements):
    """安装Python虚拟环境的依赖包
    
    参数:
        env_id: 环境ID
        env_path: 环境路径
        requirements: 依赖包列表
    """
    import subprocess
    try:
        # 获取活跃的镜像源
        mirror = get_active_mirror()
        index_url = mirror.url if mirror else 'https://pypi.org/simple/'
        
        # 构建pip命令
        pip_path = os.path.join(env_path, 'bin', 'pip')
        req_list = [req.strip() for req in requirements.split('\n') if req.strip()]
        
        log_env(env_id, f'开始安装依赖包，共{len(req_list)}个包')
        log_env(env_id, f'使用索引URL: {index_url}')
        
        # 安装每个依赖包
        for req in req_list:
            log_env(env_id, f'正在安装: {req}')
            
            cmd = [pip_path, 'install', req, '-i', index_url, '--trusted-host', index_url.split('//')[1].split('/')[0]]
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            # 实时捕获输出
            for line in process.stdout:
                log_env(env_id, line.strip())
            
            process.wait()
            
            if process.returncode == 0:
                log_env(env_id, f'成功安装: {req}')
            else:
                log_env(env_id, f'安装失败: {req}', 'ERROR')
        
        log_env(env_id, '所有依赖包安装完成')
        
    except Exception as e:
        log_env(env_id, f'安装依赖包时出错: {str(e)}', 'ERROR')