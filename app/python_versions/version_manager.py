"""Python版本管理模块

提供Python版本的下载、安装、管理和切换功能
"""

import os
import sys
import shutil
import logging
import threading
import subprocess
import requests
from datetime import datetime
from queue import Queue
from app.models.db import db, PythonVersion
from app.utils.tools import ensure_dir_exists

# 配置日志
logger = logging.getLogger(__name__)

# 设置Python版本安装根目录
PYTHON_VERSIONS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'python_versions')
# 注释掉自动创建目录的代码，按用户要求不自动创建目录
# ensure_dir_exists(PYTHON_VERSIONS_ROOT)

# 下载队列和锁，从routes模块中导入
import threading
version_queues = {}
version_queues_lock = threading.Lock()
from queue import Empty, Full

class PythonVersionManager:
    """Python版本管理类
    
    提供Python版本的下载、安装、设置默认版本和删除版本的功能
    """
    
    @staticmethod
    def add_python_version(version, download_url):
        """添加Python版本
        
        参数:
            version: Python版本号
            download_url: 下载地址
            
        返回:
            dict: 操作结果
        """
        try:
            # 检查是否已存在相同版本
            existing_version = PythonVersion.get_or_none(PythonVersion.version == version)
            if existing_version:
                return {'success': False, 'message': f'Python版本 {version} 已存在'}
            
            # 创建PythonVersion记录
            new_version = PythonVersion.create(
                version=version,
                status='pending',
                download_url=download_url,
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            
            # 创建下载队列
            with version_queues_lock:
                version_queues[new_version.id] = Queue()
            
            # 启动下载和安装线程
            threading.Thread(target=PythonVersionManager._download_and_install_python, args=(new_version.id,)).start()
            
            return {'success': True, 'message': f'开始下载和安装Python版本 {version}'}
        except Exception as e:
            logger.error(f'添加Python版本失败: {str(e)}')
            return {'success': False, 'message': f'添加Python版本失败: {str(e)}'}
    
    @staticmethod
    def _download_and_install_python(version_id, version=None, download_url=None):
        """下载并安装Python版本的线程函数
        
        参数:
            version_id: Python版本ID
            version: Python版本号（可选）
            download_url: 下载地址（可选）
        """
        try:
            # 获取版本信息，如果没有提供version和download_url，则从数据库中获取
            version_model = PythonVersion.get_by_id(version_id)
            if not version:
                version = version_model.version
            if not download_url:
                download_url = version_model.download_url
            version_model.status = 'downloading'
            version_model.update_time = datetime.now()
            version_model.save()
            
            # 记录日志到队列
            PythonVersionManager._log_to_queue(version_id, f'开始下载Python版本 {version}')
            
            # 创建临时目录
            temp_dir = os.path.join(PYTHON_VERSIONS_ROOT, f'temp_{version_id}')
            ensure_dir_exists(temp_dir)
            
            # 下载文件
            tarball_path = os.path.join(temp_dir, f'Python-{version}.tar.xz')
            try:
                PythonVersionManager._download_file(download_url, tarball_path, version_id)
            except Exception as e:
                error_msg = f'下载失败: {str(e)}'
                PythonVersionManager._handle_installation_failure(version_id, error_msg, temp_dir)
                return
            
            # 解压文件
            PythonVersionManager._log_to_queue(version_id, '下载完成，开始解压文件')
            version_model.status = 'installing'
            version_model.update_time = datetime.now()
            version_model.save()
            
            extract_dir = os.path.join(temp_dir, f'Python-{version}')
            try:
                subprocess.run(['tar', '-xf', tarball_path, '-C', temp_dir], check=True)
            except Exception as e:
                error_msg = f'解压失败: {str(e)}'
                PythonVersionManager._handle_installation_failure(version_id, error_msg, temp_dir)
                return
            
            # 配置和编译安装
            install_path = os.path.join(PYTHON_VERSIONS_ROOT, f'python-{version}')
            
            PythonVersionManager._log_to_queue(version_id, '开始配置和编译安装')
            try:
                # 配置
                subprocess.run(
                    ['./configure', f'--prefix={install_path}', '--enable-optimizations'],
                    cwd=extract_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                # 编译安装
                subprocess.run(
                    ['make', '-j4'],  # 使用4个核心进行编译
                    cwd=extract_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                subprocess.run(
                    ['make', 'install'],
                    cwd=extract_dir,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
            except Exception as e:
                error_msg = f'编译安装失败: {str(e)}'
                PythonVersionManager._handle_installation_failure(version_id, error_msg, temp_dir)
                return
            
            # 更新数据库记录
            version_model.status = 'ready'
            version_model.install_path = install_path
            version_model.update_time = datetime.now()
            version_model.save()
            
            # 清理临时文件
            shutil.rmtree(temp_dir, ignore_errors=True)
            
            PythonVersionManager._log_to_queue(version_id, f'Python版本 {version} 安装完成')
            
        except Exception as e:
            error_msg = f'安装过程中出现未知错误: {str(e)}'
            logger.error(error_msg)
            PythonVersionManager._handle_installation_failure(version_id, error_msg)
    
    @staticmethod
    def _download_file(url, save_path, version_id):
        """下载文件并显示进度
        
        参数:
            url: 下载URL
            save_path: 保存路径
            version_id: Python版本ID
        """
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        
        with open(save_path, 'wb') as file:
            for data in response.iter_content(chunk_size=8192):
                file.write(data)
                downloaded_size += len(data)
                
                # 记录下载进度
                if total_size > 0:
                    progress = downloaded_size / total_size * 100
                    PythonVersionManager._log_to_queue(version_id, f'下载进度: {progress:.1f}%')
    
    @staticmethod
    def _handle_installation_failure(version_id, error_message, temp_dir=None):
        """处理安装失败的情况
        
        参数:
            version_id: Python版本ID
            error_message: 错误消息
            temp_dir: 临时目录路径，可选
        """
        try:
            version = PythonVersion.get_by_id(version_id)
            version.status = 'failed'
            version.error_message = error_message
            version.update_time = datetime.now()
            version.save()
            
            PythonVersionManager._log_to_queue(version_id, f'Python版本 {version.version}: {error_message}')
        except:
            pass
        
        # 清理临时文件
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    @staticmethod
    def _log_to_queue(version_id, message):
        """将日志添加到队列
        
        参数:
            version_id: Python版本ID
            message: 日志消息
        """
        from app.api.routes import python_version_log_queues, python_version_log_queues_lock
        with python_version_log_queues_lock:
            if version_id in python_version_log_queues:
                try:
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                    python_version_log_queues[version_id].put(f'[{timestamp}] [INFO] {message}', block=False)
                except Exception:
                    # 队列已满或其他错误，记录到日志文件
                    logger.info(f'Python版本 {version_id} 日志: {message}')
    
    @staticmethod
    def get_version_logs(version_id):
        """获取版本的日志
        
        参数:
            version_id: Python版本ID
            
        返回:
            list: 日志消息列表
        """
        logs = []
        from app.api.routes import python_version_log_queues, python_version_log_queues_lock
        with python_version_log_queues_lock:
            if version_id in python_version_log_queues:
                queue = python_version_log_queues[version_id]
                while True:
                    try:
                        log = queue.get(block=False)
                        logs.append(log)
                    except Empty:
                        break
        return logs
    
    @staticmethod
    def get_installed_versions():
        """获取所有已安装的Python版本
        
        返回:
            list: PythonVersion对象列表
        """
        return list(PythonVersion.select())
    
    @staticmethod
    def set_default_version(version_id):
        """设置默认Python版本
        
        参数:
            version_id: Python版本ID
            
        返回:
            dict: 操作结果
        """
        try:
            version = PythonVersion.get_by_id(version_id)
            
            # 检查版本是否已安装完成
            if version.status != 'ready':
                return {'success': False, 'message': f'Python版本 {version.version} 尚未安装完成，无法设置为默认版本'}
            
            # 取消之前的默认版本
            with db.atomic():
                PythonVersion.update(is_default=False).execute()
                version.is_default = True
                version.save()
            
            return {'success': True, 'message': f'已将Python版本 {version.version} 设置为默认版本'}
        except Exception as e:
            logger.error(f'设置默认版本失败: {str(e)}')
            return {'success': False, 'message': f'设置默认版本失败: {str(e)}'}
    
    @staticmethod
    def delete_version(version_id):
        """删除Python版本
        
        参数:
            version_id: Python版本ID
            
        返回:
            dict: 操作结果
        """
        try:
            version = PythonVersion.get_by_id(version_id)
            
            # 检查是否是默认版本
            if version.is_default:
                return {'success': False, 'message': f'Python版本 {version.version} 是默认版本，无法删除'}
            
            # 检查是否有虚拟环境正在使用此版本
            from app.models.db import PythonEnv
            if PythonEnv.select().where(PythonEnv.python_version == version.version).exists():
                return {'success': False, 'message': f'Python版本 {version.version} 正在被虚拟环境使用，无法删除'}
            
            # 删除安装文件
            if version.install_path and os.path.exists(version.install_path):
                shutil.rmtree(version.install_path, ignore_errors=True)
            
            # 删除数据库记录
            version.delete_instance()
            
            # 清理队列
            with version_queues_lock:
                if version_id in version_queues:
                    del version_queues[version_id]
            
            return {'success': True, 'message': f'已删除Python版本 {version.version}'}
        except Exception as e:
            logger.error(f'删除版本失败: {str(e)}')
            return {'success': False, 'message': f'删除版本失败: {str(e)}'}
    
    @staticmethod
    def get_python_executable(version=None):
        """获取指定版本的Python可执行文件路径
        
        参数:
            version: Python版本号，可选，默认为None（使用默认版本）
            
        返回:
            str: Python可执行文件路径或None
        """
        try:
            if version:
                python_version = PythonVersion.get_or_none(PythonVersion.version == version, PythonVersion.status == 'ready')
            else:
                python_version = PythonVersion.get_or_none(PythonVersion.is_default == True, PythonVersion.status == 'ready')
            
            if python_version and python_version.install_path:
                return os.path.join(python_version.install_path, 'bin', 'python3')
            
            return None
        except:
            return None

# 初始化PythonVersionManager实例
python_version_manager = PythonVersionManager()