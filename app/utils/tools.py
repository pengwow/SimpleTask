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

# 虚拟环境根目录
ENV_ROOT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'envs')

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
def install_requirements(env_id, env_path, requirements, mirror_source=None):
    """
    安装虚拟环境的依赖包
    
    参数:
        env_id: 环境ID
        env_path: 虚拟环境路径
        requirements: 依赖包列表字符串，以逗号分隔
        mirror_source: 镜像源URL
    
    返回:
        bool: 安装是否成功
    """
    import subprocess
    import os
    import time
    
    # 初始化成功标志
    success = False
    
    try:
        # 解析依赖包列表
        req_list = [req.strip() for req in requirements.split(',') if req.strip()]
        log_env(env_id, f'开始安装依赖包，共{len(req_list)}个包')
        
        # 获取虚拟环境中的python路径
        python_path = os.path.join(env_path, 'bin', 'python')
        log_env(env_id, f'虚拟环境python路径: {python_path}')
        
        # 检查python是否存在
        if not os.path.exists(python_path):
            log_env(env_id, f'错误: python不存在: {python_path}', 'ERROR')
            return False
        
        # 为每个依赖包单独安装，避免一次性安装过多包导致的问题
        for req in req_list:
            log_env(env_id, f'开始安装: {req}')
            
            # 使用虚拟环境的python -m pip安装依赖
            cmd = [python_path, '-m', 'pip', 'install', req]
            
            # 添加基本的pip参数以提高成功率
            cmd.extend(['--timeout', '60'])
            cmd.extend(['--no-cache-dir'])
            
            # 如果提供了镜像源，添加到命令中并设置trusted-host
            if mirror_source:
                cmd.extend(['-i', mirror_source])
                # 安全地获取trusted-host，避免mirror_source为None时的错误
                try:
                    trusted_host = mirror_source.split('/')[2]
                    cmd.extend(['--trusted-host', trusted_host])
                    log_env(env_id, f'使用镜像源和trusted-host: {mirror_source}, {trusted_host}')
                except (IndexError, AttributeError):
                    log_env(env_id, f'无法解析镜像源的trusted-host: {mirror_source}', 'WARNING')
            
            log_env(env_id, f'执行命令: {cmd}')
            
            # 使用subprocess.run，不使用shell=True
            try:
                # 设置超时时间，避免长时间阻塞
                result = subprocess.run(
                    cmd,
                    shell=False,  # 使用shell=False更安全
                    capture_output=True,
                    text=True,
                    timeout=120  # 设置较长的超时时间
                )
                
                log_env(env_id, f'命令返回码: {result.returncode}')
                
                # 只记录部分输出，避免日志过大
                if result.stdout:
                    stdout_preview = result.stdout.strip().split('\n')[-3:]  # 只取最后几行
                    log_env(env_id, f'安装输出: {"\n".join(stdout_preview)}')
                
                if result.stderr:
                    stderr_preview = result.stderr.strip().split('\n')[-3:]  # 只取最后几行
                    log_env(env_id, f'警告/错误输出: {"\n".join(stderr_preview)}')
                
                # 检查是否安装成功
                if result.returncode == 0:
                    log_env(env_id, f'成功安装: {req}')
                    success = True
                else:
                    log_env(env_id, f'安装失败: {req}', 'ERROR')
                    # 不立即返回，尝试继续安装其他包
                    success = False
                    
                # 短暂休眠，避免过快执行多个pip命令
                time.sleep(1)
                
            except subprocess.TimeoutExpired:
                log_env(env_id, f'安装超时: {req}', 'ERROR')
                # 继续尝试安装下一个包
                success = False
                
            except Exception as e:
                log_env(env_id, f'执行安装命令时出错: {str(e)}', 'ERROR')
                # 继续尝试安装下一个包
                success = False
        
        # 验证安装是否成功
        if success:
            log_env(env_id, '所有依赖包安装完成')
        else:
            log_env(env_id, '部分或全部依赖包安装失败', 'WARNING')
            
    except Exception as e:
        log_env(env_id, f'安装依赖包时发生错误: {str(e)}', 'ERROR')
        success = False
    
    finally:
        # 确保函数总是能够退出
        log_env(env_id, f'依赖包安装函数执行完毕，结果: {"成功" if success else "失败"}')
        
    # 返回最终结果
    return success