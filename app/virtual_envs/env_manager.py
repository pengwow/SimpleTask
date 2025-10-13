# -*- coding: utf-8 -*-
"""Python虚拟环境管理模块

提供虚拟环境的创建、管理和操作功能
"""

import os
import sys
import time
import uuid
import logging
import threading
import subprocess
from datetime import datetime
from queue import Queue, Empty, Full

# 配置日志
logger = logging.getLogger(__name__)

# 设置虚拟环境根目录
ENV_ROOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'envs')
# 注释掉自动创建目录的代码，按用户要求不自动创建目录
# os.makedirs(ENV_ROOT_DIR, exist_ok=True)

# 日志队列字典和锁
log_queues = {}
log_queues_lock = threading.Lock()

# 导入数据库模型
from app.models.db import db, MirrorSource, PythonEnv, EnvLog
# 导入工具函数
from app.utils.tools import get_active_mirror, log_env, install_requirements

# 创建Python虚拟环境
def create_python_env(env_id):
    """创建Python虚拟环境的线程函数
    
    参数:
        env_id: 环境ID
    """
    try:
        env = PythonEnv.get_by_id(env_id)
        env.status = 'creating'
        env.update_time = datetime.now()
        env.save()
        
        # 获取活跃的镜像源
        mirror = get_active_mirror()
        if mirror:
            env.mirror_source = mirror
            env.save()
            log_env(env_id, f'使用镜像源: {mirror.url}')
        
        # 创建虚拟环境
        python_executable = f'python{env.python_version.split(".")[0]}.{env.python_version.split(".")[1]}'
        env_path = os.path.join(ENV_ROOT_DIR, f'{env.name}_{str(uuid.uuid4())[:8]}')
        
        log_env(env_id, f'开始创建虚拟环境: {env.name}')
        log_env(env_id, f'Python版本: {env.python_version}')
        log_env(env_id, f'环境路径: {env_path}')
        
        # 执行创建虚拟环境的命令
        cmd = [sys.executable, '-m', 'venv', env_path]
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        # 捕获输出日志
        for line in process.stdout:
            log_env(env_id, line.strip())
        
        process.wait()
        
        if process.returncode == 0:
            env.path = env_path
            env.status = 'ready'
            log_env(env_id, '虚拟环境创建成功')
            
            # 安装依赖包
            if env.requirements:
                install_requirements(env_id, env_path, env.requirements)
        else:
            env.status = 'failed'
            log_env(env_id, '虚拟环境创建失败', 'ERROR')
        
        env.update_time = datetime.now()
        env.save()
        
    except Exception as e:
        logger.error(f"创建环境时出错: {str(e)}")
        try:
            env = PythonEnv.get_by_id(env_id)
            env.status = 'failed'
            env.update_time = datetime.now()
            env.save()
            log_env(env_id, f'创建环境时出错: {str(e)}', 'ERROR')
        except:
            pass
    
    # 任务完成后，等待一段时间再清理队列
    time.sleep(30)
    with log_queues_lock:
        if env_id in log_queues:
            del log_queues[env_id]