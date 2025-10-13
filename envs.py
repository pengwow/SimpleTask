#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python虚拟环境管理模块

提供了强大而灵活的Python虚拟环境管理功能，支持多个Python版本，
默认使用Python 3.9.21版本。通过直观的Web界面，可以轻松创建、
编辑和管理虚拟环境，为任务提供独立的运行环境。
"""

import os
import sys
import json
import time
import uuid
import logging
import subprocess
import threading
from datetime import datetime
from flask import Flask, request, jsonify, Response, g
from peewee import SqliteDatabase, Model, CharField, TextField, IntegerField, DateTimeField, ForeignKeyField, BooleanField, DecimalField
import queue

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S,%f'
)
logger = logging.getLogger('envs_manager')

# 初始化Flask应用
app = Flask(__name__)

# 数据库配置
DATABASE = 'simpletask.db'
db = SqliteDatabase(DATABASE)

# 虚拟环境根目录
ENV_ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'python_envs')
# 注释掉自动创建目录的代码，按用户要求不自动创建目录
# if not os.path.exists(ENV_ROOT_DIR):
#     os.makedirs(ENV_ROOT_DIR)

# 日志队列，用于实时传输安装日志
log_queues = {}
log_queues_lock = threading.Lock()

# 数据库模型定义
class BaseModel(Model):
    """数据库模型基类"""
    class Meta:
        database = db

class MirrorSource(BaseModel):
    """镜像源模型
    
    属性:
        name: 镜像源名称
        url: 镜像源地址
        description: 镜像源描述
        is_active: 是否为当前活跃的镜像源
    """
    name = CharField(unique=True, max_length=50)
    url = CharField(unique=True, max_length=255)
    description = TextField(null=True)
    is_active = BooleanField(default=False)

class PythonEnv(BaseModel):
    """Python虚拟环境模型
    
    属性:
        name: 环境名称
        python_version: Python版本
        status: 环境状态（pending, creating, ready, failed）
        path: 环境路径
        requirements: 依赖项列表
        create_time: 创建时间
        update_time: 更新时间
        mirror_source: 使用的镜像源
    """
    name = CharField(unique=True, max_length=100)
    python_version = CharField(max_length=20, default='3.9.21')
    status = CharField(max_length=20, default='pending')
    path = CharField(max_length=255)
    requirements = TextField(null=True)
    create_time = DateTimeField(default=datetime.now)
    update_time = DateTimeField(default=datetime.now)
    mirror_source = ForeignKeyField(MirrorSource, backref='envs', null=True)

class EnvLog(BaseModel):
    """环境操作日志模型
    
    属性:
        env: 关联的虚拟环境
        level: 日志级别
        message: 日志消息
        timestamp: 日志时间戳
    """
    env = ForeignKeyField(PythonEnv, backref='logs')
    level = CharField(max_length=10, default='INFO')
    message = TextField()
    timestamp = DateTimeField(default=datetime.now)

# 初始化数据库
def init_db():
    """初始化数据库，创建表和默认镜像源"""
    db.connect()
    db.create_tables([MirrorSource, PythonEnv, EnvLog])
    
    # 添加默认镜像源
    default_mirrors = [
        {
            'name': 'pypi',
            'url': 'https://pypi.org/simple/',
            'description': '官方PyPI源 - 原始镜像，网络延迟可能较高',
            'is_active': False
        },
        {
            'name': 'tsinghua',
            'url': 'https://pypi.tuna.tsinghua.edu.cn/simple/',
            'description': '清华大学镜像源 - 更新及时，速度较快',
            'is_active': False
        },
        {
            'name': 'aliyun',
            'url': 'https://mirrors.aliyun.com/pypi/simple/',
            'description': '阿里云镜像源 - 资源丰富，下载速度较快',
            'is_active': True  # 默认使用阿里云镜像源
        },
        {
            'name': 'ustc',
            'url': 'https://pypi.mirrors.ustc.edu.cn/simple/',
            'description': '中国科学技术大学 - 更新速度快，适合对版本要求严格',
            'is_active': False
        },
        {
            'name': 'huawei',
            'url': 'https://repo.huaweicloud.com/repository/pypi/simple/',
            'description': '华为云镜像源 - 稳定镜像，适用多种网络环境',
            'is_active': False
        },
        {
            'name': 'tencent',
            'url': 'https://mirrors.cloud.tencent.com/pypi/simple/',
            'description': '腾讯云镜像源 - 提供全面的包资源，方便下载',
            'is_active': False
        }
    ]
    
    for mirror in default_mirrors:
        try:
            MirrorSource.get(MirrorSource.name == mirror['name'])
        except MirrorSource.DoesNotExist:
            MirrorSource.create(**mirror)
    
    db.close()

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
                except queue.Full:
                    pass
    except Exception as e:
        logger.error(f"记录日志失败: {str(e)}")

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

# 安装依赖包
def install_requirements(env_id, env_path, requirements):
    """安装Python虚拟环境的依赖包
    
    参数:
        env_id: 环境ID
        env_path: 环境路径
        requirements: 依赖包列表
    """
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

# API接口定义
@app.route('/api/envs', methods=['GET'])
def get_envs():
    """获取所有虚拟环境列表
    
    返回:
        JSON: 环境列表
    """
    try:
        envs = PythonEnv.select().order_by(PythonEnv.create_time.desc())
        result = []
        for env in envs:
            result.append({
                'id': env.id,
                'name': env.name,
                'python_version': env.python_version,
                'status': env.status,
                'create_time': env.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'update_time': env.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                'requirements': env.requirements
            })
        return jsonify({'code': 200, 'data': result})
    except Exception as e:
        logger.error(f"获取环境列表失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/envs/<int:env_id>', methods=['GET'])
def get_env(env_id):
    """获取单个虚拟环境详情
    
    参数:
        env_id: 环境ID
    
    返回:
        JSON: 环境详情
    """
    try:
        env = PythonEnv.get_by_id(env_id)
        data = {
            'id': env.id,
            'name': env.name,
            'python_version': env.python_version,
            'status': env.status,
            'path': env.path,
            'requirements': env.requirements,
            'create_time': env.create_time.strftime('%Y-%m-%d %H:%M:%S'),
            'update_time': env.update_time.strftime('%Y-%m-%d %H:%M:%S')
        }
        if env.mirror_source:
            data['mirror_source'] = {
                'name': env.mirror_source.name,
                'url': env.mirror_source.url
            }
        return jsonify({'code': 200, 'data': data})
    except Exception as e:
        logger.error(f"获取环境详情失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/envs', methods=['POST'])
def create_env():
    """创建新的Python虚拟环境
    
    请求体:
        name: 环境名称
        python_version: Python版本
        requirements: 依赖包列表
    
    返回:
        JSON: 创建结果
    """
    try:
        data = request.json
        name = data.get('name')
        python_version = data.get('python_version', '3.9.21')
        requirements = data.get('requirements', '')
        
        # 验证参数
        if not name:
            return jsonify({'code': 400, 'message': '环境名称不能为空'})
        
        # 检查环境名称是否已存在
        if PythonEnv.select().where(PythonEnv.name == name).exists():
            return jsonify({'code': 400, 'message': '环境名称已存在'})
        
        # 创建环境记录
        env = PythonEnv.create(
            name=name,
            python_version=python_version,
            requirements=requirements,
            path='',
            status='pending'
        )
        
        # 初始化日志队列
        with log_queues_lock:
            log_queues[env.id] = queue.Queue(maxsize=1000)
        
        # 启动线程创建虚拟环境
        thread = threading.Thread(target=create_python_env, args=(env.id,))
        thread.daemon = True
        thread.start()
        
        return jsonify({'code': 200, 'message': '环境创建任务已提交', 'data': {'id': env.id}})
    except Exception as e:
        logger.error(f"创建环境失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/envs/<int:env_id>', methods=['PUT'])
def update_env(env_id):
    """更新Python虚拟环境
    
    参数:
        env_id: 环境ID
    
    请求体:
        requirements: 新的依赖包列表
    
    返回:
        JSON: 更新结果
    """
    try:
        data = request.json
        requirements = data.get('requirements')
        
        env = PythonEnv.get_by_id(env_id)
        
        # 只有ready状态的环境才能更新
        if env.status != 'ready':
            return jsonify({'code': 400, 'message': '只有就绪状态的环境才能更新'})
        
        if requirements is not None:
            env.requirements = requirements
            env.update_time = datetime.now()
            env.save()
            
            # 重新安装依赖包
            with log_queues_lock:
                log_queues[env.id] = queue.Queue(maxsize=1000)
            
            thread = threading.Thread(target=install_requirements, args=(env_id, env.path, requirements))
            thread.daemon = True
            thread.start()
        
        return jsonify({'code': 200, 'message': '环境更新成功'})
    except Exception as e:
        logger.error(f"更新环境失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/envs/<int:env_id>', methods=['DELETE'])
def delete_env(env_id):
    """删除Python虚拟环境
    
    参数:
        env_id: 环境ID
    
    返回:
        JSON: 删除结果
    """
    try:
        env = PythonEnv.get_by_id(env_id)
        
        # 删除环境目录
        if env.path and os.path.exists(env.path):
            import shutil
            shutil.rmtree(env.path)
        
        # 删除数据库记录
        env.delete_instance(recursive=True)
        
        # 清理日志队列
        with log_queues_lock:
            if env_id in log_queues:
                del log_queues[env_id]
        
        return jsonify({'code': 200, 'message': '环境删除成功'})
    except Exception as e:
        logger.error(f"删除环境失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/envs/<int:env_id>/logs', methods=['GET'])
def get_env_logs(env_id):
    """获取环境的历史日志
    
    参数:
        env_id: 环境ID
    
    返回:
        JSON: 日志列表
    """
    try:
        logs = EnvLog.select().where(EnvLog.env == env_id).order_by(EnvLog.timestamp)
        result = []
        for log in logs:
            result.append({
                'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'level': log.level,
                'message': log.message
            })
        return jsonify({'code': 200, 'data': result})
    except Exception as e:
        logger.error(f"获取环境日志失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/envs/<int:env_id>/log_stream')
def log_stream(env_id):
    """实时获取环境的安装日志流
    
    参数:
        env_id: 环境ID
    
    返回:
        Response: 事件流响应
    """
    def event_stream():
        # 首先发送所有历史日志
        try:
            logs = EnvLog.select().where(EnvLog.env == env_id).order_by(EnvLog.timestamp)
            for log in logs:
                timestamp = log.timestamp.strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
                yield f'data: [{timestamp}] [{log.level}] {log.message}\n\n'
        except:
            pass
        
        # 初始化日志队列
        with log_queues_lock:
            if env_id not in log_queues:
                log_queues[env_id] = queue.Queue(maxsize=1000)
        
        # 实时发送新日志
        while True:
            try:
                with log_queues_lock:
                    if env_id not in log_queues:
                        break
                    queue_ref = log_queues[env_id]
                
                try:
                    log = queue_ref.get(timeout=1)
                    yield f'data: {log}\n\n'
                except queue.Empty:
                    # 检查环境是否已完成创建
                    try:
                        env = PythonEnv.get_by_id(env_id)
                        if env.status in ['ready', 'failed']:
                            # 检查是否还有日志需要发送
                            if queue_ref.empty():
                                time.sleep(1)  # 等待1秒确保所有日志都已处理
                                break
                    except:
                        break
                    continue
                except queue.Full:
                    continue
            except GeneratorExit:
                break
            except Exception as e:
                logger.error(f"日志流出错: {str(e)}")
                break
            
            time.sleep(0.1)  # 避免CPU占用过高
        
        # 发送结束信号
        yield 'data: [STREAM_END]\n\n'
    
    return Response(event_stream(), mimetype='text/event-stream')

@app.route('/api/mirrors', methods=['GET'])
def get_mirrors():
    """获取所有镜像源列表
    
    返回:
        JSON: 镜像源列表
    """
    try:
        mirrors = MirrorSource.select()
        result = []
        for mirror in mirrors:
            result.append({
                'id': mirror.id,
                'name': mirror.name,
                'url': mirror.url,
                'description': mirror.description,
                'is_active': mirror.is_active
            })
        return jsonify({'code': 200, 'data': result})
    except Exception as e:
        logger.error(f"获取镜像源列表失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/mirrors/<int:mirror_id>', methods=['GET'])
def get_mirror(mirror_id):
    """获取单个镜像源详情
    
    参数:
        mirror_id: 镜像源ID
    
    返回:
        JSON: 镜像源详情
    """
    try:
        mirror = MirrorSource.get_by_id(mirror_id)
        data = {
            'id': mirror.id,
            'name': mirror.name,
            'url': mirror.url,
            'description': mirror.description,
            'is_active': mirror.is_active
        }
        return jsonify({'code': 200, 'data': data})
    except Exception as e:
        logger.error(f"获取镜像源详情失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/mirrors', methods=['POST'])
def create_mirror():
    """创建新的镜像源
    
    请求体:
        name: 镜像源名称
        url: 镜像源地址
        description: 镜像源描述
    
    返回:
        JSON: 创建结果
    """
    try:
        data = request.json
        name = data.get('name')
        url = data.get('url')
        description = data.get('description', '')
        
        # 验证参数
        if not name or not url:
            return jsonify({'code': 400, 'message': '名称和地址不能为空'})
        
        # 检查名称和地址是否已存在
        if MirrorSource.select().where(MirrorSource.name == name).exists():
            return jsonify({'code': 400, 'message': '镜像源名称已存在'})
        
        if MirrorSource.select().where(MirrorSource.url == url).exists():
            return jsonify({'code': 400, 'message': '镜像源地址已存在'})
        
        # 创建镜像源
        mirror = MirrorSource.create(
            name=name,
            url=url,
            description=description,
            is_active=False
        )
        
        return jsonify({'code': 200, 'message': '镜像源创建成功', 'data': {'id': mirror.id}})
    except Exception as e:
        logger.error(f"创建镜像源失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/mirrors/<int:mirror_id>', methods=['PUT'])
def update_mirror(mirror_id):
    """更新镜像源
    
    参数:
        mirror_id: 镜像源ID
    
    请求体:
        name: 镜像源名称
        url: 镜像源地址
        description: 镜像源描述
        is_active: 是否设为活跃
    
    返回:
        JSON: 更新结果
    """
    try:
        data = request.json
        mirror = MirrorSource.get_by_id(mirror_id)
        
        # 更新字段
        if 'name' in data and data['name'] != mirror.name:
            if MirrorSource.select().where(MirrorSource.name == data['name']).exists():
                return jsonify({'code': 400, 'message': '镜像源名称已存在'})
            mirror.name = data['name']
        
        if 'url' in data and data['url'] != mirror.url:
            if MirrorSource.select().where(MirrorSource.url == data['url']).exists():
                return jsonify({'code': 400, 'message': '镜像源地址已存在'})
            mirror.url = data['url']
        
        if 'description' in data:
            mirror.description = data['description']
        
        # 处理激活状态
        if 'is_active' in data and data['is_active']:
            # 先取消其他所有镜像源的激活状态
            MirrorSource.update(is_active=False).execute()
            mirror.is_active = True
        elif 'is_active' in data and not data['is_active']:
            mirror.is_active = False
        
        mirror.save()
        
        return jsonify({'code': 200, 'message': '镜像源更新成功'})
    except Exception as e:
        logger.error(f"更新镜像源失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/mirrors/<int:mirror_id>', methods=['DELETE'])
def delete_mirror(mirror_id):
    """删除镜像源
    
    参数:
        mirror_id: 镜像源ID
    
    返回:
        JSON: 删除结果
    """
    try:
        mirror = MirrorSource.get_by_id(mirror_id)
        
        # 不能删除最后一个镜像源
        if MirrorSource.select().count() <= 1:
            return jsonify({'code': 400, 'message': '至少保留一个镜像源'})
        
        # 如果删除的是活跃镜像源，自动激活第一个可用的镜像源
        if mirror.is_active:
            first_mirror = MirrorSource.select().where(MirrorSource.id != mirror_id).first()
            if first_mirror:
                first_mirror.is_active = True
                first_mirror.save()
        
        mirror.delete_instance()
        
        return jsonify({'code': 200, 'message': '镜像源删除成功'})
    except Exception as e:
        logger.error(f"删除镜像源失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/mirrors/active', methods=['GET'])
def get_active_mirror_api():
    """获取当前活跃的镜像源
    
    返回:
        JSON: 活跃的镜像源
    """
    try:
        mirror = get_active_mirror()
        if mirror:
            data = {
                'id': mirror.id,
                'name': mirror.name,
                'url': mirror.url,
                'description': mirror.description
            }
            return jsonify({'code': 200, 'data': data})
        else:
            return jsonify({'code': 404, 'message': '没有活跃的镜像源'})
    except Exception as e:
        logger.error(f"获取活跃镜像源失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

# 应用启动时初始化数据库
@app.before_request
def before_request():
    """请求处理前连接数据库"""
    if db.is_closed():
        db.connect()

@app.after_request
def after_request(response):
    """请求处理后关闭数据库"""
    if not db.is_closed():
        db.close()
    return response

# 主函数
if __name__ == '__main__':
    # 初始化数据库
    init_db()
    
    # 启动Flask应用
    app.run(host='0.0.0.0', port=5001, debug=True)