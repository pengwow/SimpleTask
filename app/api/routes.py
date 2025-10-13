# -*- coding: utf-8 -*-
"""API接口定义

提供项目的所有RESTful API接口
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
from flask import Flask, request, jsonify, Response

# 导入数据库模型
from app.models.db import db, MirrorSource, PythonEnv, EnvLog, PythonVersion, Project, ProjectTag
# 导入工具函数
from app.utils.tools import get_active_mirror, log_env, ENV_ROOT_DIR, log_queues_lock, log_queues
# 导入虚拟环境管理函数
from app.virtual_envs.env_manager import create_python_env, install_requirements
# 导入Python版本管理函数
from app.python_versions.version_manager import PythonVersionManager
# 导入项目管理模块
from app.projects.project_manager import project_manager
# 导入任务管理模块
from app.tasks.task_manager import task_manager

# 初始化Flask应用
app = Flask(__name__)

# Python版本管理日志队列
python_version_log_queues = {}
python_version_log_queues_lock = threading.Lock()

# 项目管理相关的路由
@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取项目列表
    
    查询参数:
        page: 页码，默认为1
        per_page: 每页数量，默认为10
        search: 搜索关键词
        tags: 标签筛选，以逗号分隔
        
    返回:
        JSON: 项目列表和分页信息
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        tags_str = request.args.get('tags', '')
        
        # 解析标签参数
        tags = [tag.strip() for tag in tags_str.split(',')] if tags_str else None
        
        # 调用项目管理模块获取项目列表
        result = project_manager.get_projects(page=page, per_page=per_page, search=search, tags=tags)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取项目列表失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取项目列表失败: {str(e)}'}), 500

@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目
    
    请求体:
        name: 项目名称
        description: 项目描述
        work_path: 工作路径
        source_type: 项目来源类型 (zip, git)
        source_url: Git仓库地址
        branch: Git分支
        git_username: Git用户名
        git_password: Git密码
        tags: 项目标签列表
        
    返回:
        JSON: 操作结果
    """
    try:
        # 获取请求数据
        data = request.json
        
        # 调用项目管理模块创建项目
        result = project_manager.create_project(
            name=data.get('name'),
            description=data.get('description'),
            work_path=data.get('work_path', '/'),
            source_type=data.get('source_type', 'zip'),
            source_url=data.get('source_url'),
            branch=data.get('branch', 'main'),
            git_username=data.get('git_username'),
            git_password=data.get('git_password'),
            tags=data.get('tags')
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'创建项目失败: {str(e)}')
        return jsonify({'success': False, 'message': f'创建项目失败: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """获取项目详情
    
    参数:
        project_id: 项目ID
        
    返回:
        JSON: 项目详情
    """
    try:
        # 调用项目管理模块获取项目详情
        result = project_manager.get_project(project_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取项目详情失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取项目详情失败: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目信息
    
    参数:
        project_id: 项目ID
        
    请求体:
        name: 项目名称
        description: 项目描述
        work_path: 工作路径
        tags: 项目标签列表
        
    返回:
        JSON: 操作结果
    """
    try:
        # 获取请求数据
        data = request.json
        
        # 调用项目管理模块更新项目
        result = project_manager.update_project(
            project_id=project_id,
            name=data.get('name'),
            description=data.get('description'),
            work_path=data.get('work_path'),
            tags=data.get('tags')
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'更新项目失败: {str(e)}')
        return jsonify({'success': False, 'message': f'更新项目失败: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目
    
    参数:
        project_id: 项目ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 调用项目管理模块删除项目
        result = project_manager.delete_project(project_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'删除项目失败: {str(e)}')
        return jsonify({'success': False, 'message': f'删除项目失败: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/upload', methods=['POST'])
def upload_project_file(project_id):
    """上传项目ZIP文件
    
    参数:
        project_id: 项目ID
        
    请求体:
        file: ZIP文件
        
    返回:
        JSON: 操作结果
    """
    try:
        # 检查是否有文件上传
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件上传'}), 400
        
        file = request.files['file']
        
        # 检查文件是否为空
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        # 检查文件类型
        if not file.filename.endswith('.zip'):
            return jsonify({'success': False, 'message': '只支持ZIP文件'}), 400
        
        # 调用项目管理模块上传文件
        result = project_manager.upload_project_zip(project_id, file)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'上传项目文件失败: {str(e)}')
        return jsonify({'success': False, 'message': f'上传项目文件失败: {str(e)}'}), 500

@app.route('/api/projects/<int:project_id>/files/<path:file_path>', methods=['GET'])
def get_project_file(project_id, file_path):
    """获取项目文件内容
    
    参数:
        project_id: 项目ID
        file_path: 文件路径
        
    返回:
        JSON: 文件内容
    """
    try:
        # 调用项目管理模块获取文件内容
        result = project_manager.get_project_file(project_id, file_path)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 404
    except Exception as e:
        logger.error(f'获取项目文件失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取项目文件失败: {str(e)}'}), 500

@app.route('/api/project_tags', methods=['GET'])
def get_project_tags():
    """获取所有项目标签
    
    返回:
        JSON: 标签列表
    """
    try:
        # 调用项目管理模块获取标签列表
        result = project_manager.get_tags()
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取项目标签失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取项目标签失败: {str(e)}'}), 500

# API接口定义 - 虚拟环境管理
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
            log_queues[env.id] = Queue(maxsize=1000)
        
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
                log_queues[env.id] = Queue(maxsize=1000)
            
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
                log_queues[env_id] = Queue(maxsize=1000)
        
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
                except Empty:
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
                except Full:
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

# API接口定义 - 镜像源管理
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

# 数据库连接管理
@app.before_request
def before_request():
    """请求处理前连接数据库"""
    if db.is_closed():
        db.connect()

# API接口定义 - Python版本管理
@app.route('/api/python_versions', methods=['GET'])
def get_python_versions():
    """获取所有Python版本列表
    
    返回:
        JSON: Python版本列表
    """
    try:
        versions = PythonVersion.select().order_by(PythonVersion.version.desc())
        result = []
        for version in versions:
            result.append({
                'id': version.id,
                'version': version.version,
                'status': version.status,
                'is_default': version.is_default,
                'download_url': version.download_url,
                'install_path': version.install_path,
                'create_time': version.create_time.strftime('%Y-%m-%d %H:%M:%S') if version.create_time else None,
                'update_time': version.update_time.strftime('%Y-%m-%d %H:%M:%S') if version.update_time else None,
                'error_message': version.error_message
            })
        return jsonify({'code': 200, 'data': result})
    except Exception as e:
        logger.error(f"获取Python版本列表失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/python_versions/<int:version_id>', methods=['GET'])
def get_python_version(version_id):
    """获取单个Python版本详情
    
    参数:
        version_id: 版本ID
    
    返回:
        JSON: Python版本详情
    """
    try:
        version = PythonVersion.get_by_id(version_id)
        data = {
            'id': version.id,
            'version': version.version,
            'status': version.status,
            'is_default': version.is_default,
            'download_url': version.download_url,
            'install_path': version.install_path,
            'create_time': version.create_time.strftime('%Y-%m-%d %H:%M:%S') if version.create_time else None,
            'update_time': version.update_time.strftime('%Y-%m-%d %H:%M:%S') if version.update_time else None,
            'error_message': version.error_message
        }
        return jsonify({'code': 200, 'data': data})
    except Exception as e:
        logger.error(f"获取Python版本详情失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/python_versions', methods=['POST'])
def add_python_version():
    """添加Python版本
    
    请求体:
        version: 版本名称
        download_url: 下载地址
    
    返回:
        JSON: 添加结果
    """
    try:
        data = request.json
        version = data.get('version')
        download_url = data.get('download_url')
        
        # 验证参数
        if not version or not download_url:
            return jsonify({'code': 400, 'message': '版本名称和下载地址不能为空'})
        
        # 验证下载地址格式
        if not download_url.endswith('.tar.xz'):
            return jsonify({'code': 400, 'message': '请下载.tar.xz格式的安装包'})
        
        # 检查版本是否已存在
        if PythonVersion.select().where(PythonVersion.version == version).exists():
            return jsonify({'code': 400, 'message': 'Python版本已存在'})
        
        # 创建版本记录
        python_version = PythonVersion.create(
            version=version,
            status='pending',
            download_url=download_url,
            install_path='',
            is_default=False
        )
        
        # 初始化日志队列
        with python_version_log_queues_lock:
            python_version_log_queues[python_version.id] = Queue(maxsize=1000)
        
        # 启动线程下载和安装Python版本
        thread = threading.Thread(target=PythonVersionManager._download_and_install_python, args=(python_version.id, version, download_url))
        thread.daemon = True
        thread.start()
        
        return jsonify({'code': 200, 'message': 'Python版本添加成功，正在下载安装', 'data': {'id': python_version.id}})
    except Exception as e:
        logger.error(f"添加Python版本失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/python_versions/<int:version_id>/set_default', methods=['POST'])
def set_default_python_version(version_id):
    """设置默认Python版本
    
    参数:
        version_id: 版本ID
    
    返回:
        JSON: 设置结果
    """
    try:
        version = PythonVersion.get_by_id(version_id)
        
        # 检查版本是否已安装完成
        if version.status != 'ready':
            return jsonify({'code': 400, 'message': '只有已安装完成的Python版本才能设为默认'})
        
        # 设置默认版本
        PythonVersionManager.set_default_version(version_id)
        
        return jsonify({'code': 200, 'message': '默认Python版本设置成功'})
    except Exception as e:
        logger.error(f"设置默认Python版本失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/python_versions/<int:version_id>', methods=['DELETE'])
def delete_python_version(version_id):
    """删除Python版本
    
    参数:
        version_id: 版本ID
    
    返回:
        JSON: 删除结果
    """
    try:
        version = PythonVersion.get_by_id(version_id)
        
        # 不能删除默认版本
        if version.is_default:
            return jsonify({'code': 400, 'message': '不能删除默认Python版本，请先设置其他版本为默认'})
        
        # 删除版本
        PythonVersionManager.delete_version(version_id)
        
        # 清理日志队列
        with python_version_log_queues_lock:
            if version_id in python_version_log_queues:
                del python_version_log_queues[version_id]
        
        return jsonify({'code': 200, 'message': 'Python版本删除成功'})
    except Exception as e:
        logger.error(f"删除Python版本失败: {str(e)}")
        return jsonify({'code': 500, 'message': str(e)})

@app.route('/api/python_versions/<int:version_id>/log_stream')
def python_version_log_stream(version_id):
    """实时获取Python版本安装日志流
    
    参数:
        version_id: 版本ID
    
    返回:
        Response: 事件流响应
    """
    def event_stream():
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
                        version = PythonVersion.get_by_id(version_id)
                        if version.status in ['ready', 'failed']:
                            # 检查是否还有日志需要发送
                            if queue_ref.empty():
                                time.sleep(1)  # 等待1秒确保所有日志都已处理
                                break
                    except:
                        break
                    continue
                except Full:
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

# 任务管理相关的路由
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表
    
    查询参数:
        page: 页码，默认为1
        per_page: 每页数量，默认为10
        search: 搜索关键词
        project_id: 项目ID过滤
        python_env_id: Python虚拟环境ID过滤
        is_active: 任务状态过滤
        
    返回:
        JSON: 任务列表和分页信息
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        search = request.args.get('search', '')
        project_id = request.args.get('project_id', type=int)
        python_env_id = request.args.get('python_env_id', type=int)
        is_active = request.args.get('is_active')
        
        # 处理布尔值参数
        if is_active is not None:
            is_active = is_active.lower() == 'true'
        
        # 调用任务管理模块获取任务列表
        result = task_manager.get_tasks(
            page=page, 
            per_page=per_page, 
            search=search,
            project_id=project_id,
            python_env_id=python_env_id,
            is_active=is_active
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取任务列表失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取任务列表失败: {str(e)}'}), 500

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建新任务
    
    请求体:
        name: 任务名称
        description: 任务描述
        project_id: 项目ID（可选）
        python_env_id: Python虚拟环境ID
        command: 执行命令
        schedule_type: 调度类型 (immediate, interval, one-time, cron)
        schedule_config: 调度配置（JSON字符串）
        max_instances: 最大并发实例数
        
    返回:
        JSON: 操作结果
    """
    try:
        # 获取请求数据
        data = request.json
        
        # 调用任务管理模块创建任务
        result = task_manager.create_task(
            name=data.get('name'),
            description=data.get('description'),
            project_id=data.get('project_id'),
            python_env_id=data.get('python_env_id'),
            command=data.get('command'),
            schedule_type=data.get('schedule_type'),
            schedule_config=data.get('schedule_config'),
            max_instances=data.get('max_instances', 1)
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'创建任务失败: {str(e)}')
        return jsonify({'success': False, 'message': f'创建任务失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """获取任务详情
    
    参数:
        task_id: 任务ID
        
    返回:
        JSON: 任务详情
    """
    try:
        # 调用任务管理模块获取任务详情
        result = task_manager.get_task(task_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取任务详情失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取任务详情失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务信息
    
    参数:
        task_id: 任务ID
        
    请求体:
        name: 任务名称
        description: 任务描述
        project_id: 项目ID
        python_env_id: Python虚拟环境ID
        command: 执行命令
        schedule_type: 调度类型
        schedule_config: 调度配置
        max_instances: 最大并发实例数
        
    返回:
        JSON: 操作结果
    """
    try:
        # 获取请求数据
        data = request.json
        
        # 调用任务管理模块更新任务
        result = task_manager.update_task(task_id, **data)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'更新任务失败: {str(e)}')
        return jsonify({'success': False, 'message': f'更新任务失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务
    
    参数:
        task_id: 任务ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 调用任务管理模块删除任务
        result = task_manager.delete_task(task_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'删除任务失败: {str(e)}')
        return jsonify({'success': False, 'message': f'删除任务失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>/start', methods=['POST'])
def start_task(task_id):
    """启动任务调度
    
    参数:
        task_id: 任务ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 调用任务管理模块启动任务
        result = task_manager.start_task(task_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'启动任务失败: {str(e)}')
        return jsonify({'success': False, 'message': f'启动任务失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>/pause', methods=['POST'])
def pause_task(task_id):
    """暂停任务调度
    
    参数:
        task_id: 任务ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 调用任务管理模块暂停任务
        result = task_manager.pause_task(task_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'暂停任务失败: {str(e)}')
        return jsonify({'success': False, 'message': f'暂停任务失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>/executions', methods=['GET'])
def get_task_executions(task_id):
    """获取任务执行历史记录
    
    查询参数:
        page: 页码，默认为1
        per_page: 每页数量，默认为10
        status: 执行状态过滤
        
    返回:
        JSON: 执行历史记录
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        status = request.args.get('status')
        
        # 调用任务管理模块获取执行历史
        result = task_manager.get_task_executions(
            task_id=task_id, 
            page=page, 
            per_page=per_page,
            status=status
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取任务执行历史失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取任务执行历史失败: {str(e)}'}), 500

@app.route('/api/executions/<int:execution_id>/logs', methods=['GET'])
def get_execution_logs(execution_id):
    """获取任务执行日志
    
    查询参数:
        page: 页码，默认为1
        per_page: 每页数量，默认为50
        level: 日志级别过滤
        search: 关键词搜索
        
    返回:
        JSON: 执行日志
    """
    try:
        # 获取查询参数
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        level = request.args.get('level')
        search = request.args.get('search', '')
        
        # 调用任务管理模块获取执行日志
        result = task_manager.get_task_logs(
            execution_id=execution_id, 
            page=page, 
            per_page=per_page,
            level=level,
            search=search
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取任务执行日志失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取任务执行日志失败: {str(e)}'}), 500

@app.route('/api/executions/<int:execution_id>/terminate', methods=['POST'])
def terminate_execution(execution_id):
    """强制终止任务执行
    
    参数:
        execution_id: 执行实例ID
        
    返回:
        JSON: 操作结果
    """
    try:
        # 调用任务管理模块强制终止任务
        result = task_manager.terminate_task_execution(execution_id)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'强制终止任务执行失败: {str(e)}')
        return jsonify({'success': False, 'message': f'强制终止任务执行失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>/running_instances', methods=['GET'])
def get_running_instances(task_id):
    """获取任务运行实例数
    
    参数:
        task_id: 任务ID
        
    返回:
        JSON: 运行实例数量
    """
    try:
        # 调用任务管理模块获取运行实例数
        count = task_manager.get_running_instances_count(task_id)
        
        return jsonify({'success': True, 'count': count})
    except Exception as e:
        logger.error(f'获取任务运行实例数失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取任务运行实例数失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>/stats', methods=['GET'])
def get_task_stats(task_id):
    """获取任务执行统计信息
    
    参数:
        task_id: 任务ID
        
    返回:
        JSON: 执行统计信息
    """
    try:
        # 调用任务管理模块获取执行统计信息
        stats = task_manager.get_task_execution_stats(task_id)
        
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        logger.error(f'获取任务执行统计信息失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取任务执行统计信息失败: {str(e)}'}), 500

@app.route('/api/tasks/<int:task_id>/executions/<int:execution_id>/realtime_logs', methods=['GET'])
def get_realtime_logs(task_id, execution_id):
    """获取实时日志
    
    参数:
        task_id: 任务ID
        execution_id: 执行实例ID
        
    查询参数:
        last_timestamp: 上次获取日志的时间戳
        limit: 返回日志数量上限
        
    返回:
        JSON: 实时日志
    """
    try:
        # 获取查询参数
        last_timestamp = request.args.get('last_timestamp')
        limit = request.args.get('limit', 100, type=int)
        
        # 调用任务管理模块获取实时日志
        result = task_manager.get_realtime_logs(
            task_id=task_id,
            execution_id=execution_id,
            last_timestamp=last_timestamp,
            limit=limit
        )
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f'获取实时日志失败: {str(e)}')
        return jsonify({'success': False, 'message': f'获取实时日志失败: {str(e)}'}), 500

# 数据库连接管理
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