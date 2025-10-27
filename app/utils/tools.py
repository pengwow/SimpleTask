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
from app.db import get_db, MirrorSource, PythonEnv, EnvLog

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

# 导入配置管理器
from app.config.config_manager import config_manager

# 从配置中获取虚拟环境根目录
ENV_ROOT_DIR = config_manager.get_env_root_dir()

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
    db = next(get_db())
    try:
        # 查找活跃的镜像源
        active_mirror = db.query(MirrorSource).filter(MirrorSource.is_active == True).first()
        if active_mirror:
            return active_mirror
        
        # 如果没有活跃的镜像源，返回阿里云作为默认
        aliyun_mirror = db.query(MirrorSource).filter(MirrorSource.name == 'aliyun').first()
        return aliyun_mirror
    except Exception as e:
        logger.error(f"获取活跃镜像源失败: {str(e)}")
        return None
    finally:
        db.close()

# 记录环境日志
def log_env(env_id, message, level='INFO'):
    """记录环境操作日志
    
    参数:
        env_id: 环境ID
        message: 日志消息
        level: 日志级别
    """
    db = next(get_db())
    try:
        env = db.query(PythonEnv).filter(PythonEnv.id == env_id).first()
        if not env:
            return
        
        # 保存到数据库
        env_log = EnvLog(env_id=env_id, level=level, message=message)
        db.add(env_log)
        db.commit()
        
        # 发送到实时日志队列
        with log_queues_lock:
            if env_id in log_queues:
                try:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                    log_queues[env_id].put(f'[{timestamp}] [{level}] {message}\n')
                except Full:
                    pass
    except Exception as e:
        if 'db' in locals():
            db.rollback()
        logger.error(f"记录日志失败: {str(e)}")
    finally:
        if 'db' in locals():
            db.close()

# 安装依赖包
def install_requirements(env_id, env_path, requirements=None, mirror_source=None):
    """安装Python依赖包
    
    参数:
        env_id: 环境ID
        env_path: 虚拟环境路径
        requirements: 依赖包列表，字符串格式，每行一个包
        mirror_source: 可选的pip镜像源URL
    
    返回:
        bool: 安装是否成功
    """
    # 确保导入语句在函数内部
    import os
    import tempfile
    import subprocess
    
    # 初始化成功标志和临时文件路径
    success = False
    temp_file_path = None
    
    try:
        log_env(env_id, '开始执行install_requirements函数')
        
        # 获取虚拟环境中的python路径
        python_path = os.path.join(env_path, 'bin', 'python')
        log_env(env_id, f'虚拟环境python路径: {python_path}')
        
        # 检查python是否存在
        if not os.path.exists(python_path):
            log_env(env_id, f'错误: python不存在: {python_path}', 'ERROR')
            return False
        
        # 清理并规范化requirements文本，处理不同的换行符
        if requirements:
            # 处理Windows和Unix风格的换行符
            requirements = requirements.replace('\r\n', '\n').strip()
            
            # 计算依赖包数量
            req_count = len([req.strip() for req in requirements.split('\n') if req.strip()])
            log_env(env_id, f'开始安装依赖包，共{req_count}个包')
        else:
            log_env(env_id, '没有需要安装的依赖包')
            success = True
            return success
        
        # 创建临时文件来存储requirements
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
                temp_file.write(requirements)
                temp_file_path = temp_file.name
            log_env(env_id, f'已创建临时requirements文件: {temp_file_path}')
        except Exception as e:
            log_env(env_id, f'创建临时文件失败: {str(e)}', 'ERROR')
            return False
        
        # 构建pip命令，使用-r参数从文件安装
        cmd = [python_path, '-m', 'pip', 'install', '-r', temp_file_path]
        
        # 添加基本的pip参数以提高成功率
        cmd.extend(['--timeout', '30'])
        cmd.extend(['--no-cache-dir'])
        
        # 如果提供了镜像源，添加到命令中
        if mirror_source:
            cmd.extend(['-i', mirror_source])
        
        log_env(env_id, f'准备执行命令: {cmd}')
        
        # 执行pip安装命令
        try:
            # 确保临时文件存在
            if not os.path.exists(temp_file_path):
                log_env(env_id, f'错误: 临时文件不存在: {temp_file_path}', 'ERROR')
                success = False
                return success
                
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # 检查执行结果
            if result.returncode == 0:
                log_env(env_id, '依赖包安装成功')
                success = True
            else:
                log_env(env_id, f'依赖包安装失败，返回码: {result.returncode}', 'ERROR')
                log_env(env_id, f'错误输出: {result.stderr}', 'ERROR')
                success = False
        except subprocess.TimeoutExpired:
            log_env(env_id, 'pip安装命令执行超时', 'ERROR')
            success = False
        except Exception as e:
            log_env(env_id, f'执行pip命令时发生异常: {str(e)}', 'ERROR')
            success = False
        
            
    except Exception as e:
        log_env(env_id, f'安装依赖包时发生错误: {str(e)}', 'ERROR')
        success = False
    
    finally:
        # 清理临时文件 - 确保在任何情况下都尝试清理
        try:
            if temp_file_path and os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
                log_env(env_id, f'已清理临时文件: {temp_file_path}')
        except Exception as e:
            log_env(env_id, f'清理临时文件失败: {str(e)}', 'WARNING')
        
        # 确保函数总是能够退出并记录最终结果
        log_env(env_id, f'依赖包安装函数执行完毕，结果: {"成功" if success else "失败"}')
        
    # 返回最终结果
    return success

if __name__ == '__main__':
    install_requirements(1, '/Users/liupeng/workspace/SimpleTask/envs/test-env-minimal', 'pip')