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

# 导入配置管理器
from app.config.config_manager import config_manager

# 配置日志
logger = logging.getLogger(__name__)

# 从配置中获取虚拟环境根目录
ENV_ROOT_DIR = config_manager.get_env_root_dir()
logger.info(f"虚拟环境根目录设置为: {ENV_ROOT_DIR}")

# 注释掉自动创建目录的代码，按用户要求不自动创建目录
# os.makedirs(ENV_ROOT_DIR, exist_ok=True)

# 日志队列字典和锁
log_queues = {}
log_queues_lock = threading.Lock()

# 导入数据库模型和会话
from app.db.database import SessionLocal
from app.db.models import MirrorSource, PythonEnv, EnvLog
# 导入工具函数
from app.utils.tools import get_active_mirror, log_env, install_requirements

# 创建Python虚拟环境
def create_python_env(env_id):
    """创建Python虚拟环境的线程函数
    
    参数:
        env_id: 环境ID
    """
    db = SessionLocal()
    try:
        # 使用SQLAlchemy查询获取环境
        env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
        if not env:
            logger.error(f"环境ID {env_id} 不存在")
            return
            
        env.status = 'creating'
        env.update_time = datetime.now()
        db.commit()
        
        # 获取活跃的镜像源
        mirror = get_active_mirror()
        if mirror:
            env.mirror_source_id = mirror.id
            db.commit()
            log_env(env_id, f'使用镜像源: {mirror.url}')
        
        # 检查并创建虚拟环境根目录
        if not os.path.exists(ENV_ROOT_DIR):
            try:
                os.makedirs(ENV_ROOT_DIR, exist_ok=True)
                log_env(env_id, f'创建虚拟环境根目录: {ENV_ROOT_DIR}')
                logger.info(f'已创建虚拟环境根目录: {ENV_ROOT_DIR}')
            except Exception as e:
                log_env(env_id, f'创建虚拟环境根目录失败: {str(e)}', 'ERROR')
                logger.error(f'创建虚拟环境根目录失败: {str(e)}')
                env.status = 'failed'
                env.update_time = datetime.now()
                db.commit()
                return
        
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
            env.status = 'installing'
            log_env(env_id, '虚拟环境创建成功')
            db.commit()  # 先提交环境路径和状态
            
            # 安装依赖包
            if env.requirements:
                install_requirements(env_id, env_path, env.requirements)
                
            # 依赖包安装完成后更新状态
            env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()  # 重新获取最新环境
            if env:
                env.status = 'ready'
                env.update_time = datetime.now()
                db.commit()
        else:
            env.status = 'failed'
            log_env(env_id, '虚拟环境创建失败', 'ERROR')
        
        env.update_time = datetime.now()
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"创建环境时出错: {str(e)}")
        try:
            env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
            if env:
                env.status = 'failed'
                env.update_time = datetime.now()
                db.commit()
                log_env(env_id, f'创建环境时出错: {str(e)}', 'ERROR')
        except:
            pass
    finally:
        db.close()
    
    # 任务完成后，等待一段时间再清理队列
    time.sleep(30)
    with log_queues_lock:
        if env_id in log_queues:
            del log_queues[env_id]