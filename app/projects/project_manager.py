#!/usr/bin/env python3
"""项目管理模块

提供项目的创建、配置、导入和管理功能
"""

import os
import sys
import shutil
import logging
import threading
import subprocess
import tempfile
import zipfile
import requests
from datetime import datetime
from pathlib import Path
from app.models.db import db, Project, ProjectTag, ProjectToTag
# 导入工具函数
import os
from app.utils.tools import ensure_dir_exists

# 配置日志
logger = logging.getLogger(__name__)

# 设置项目根目录
PROJECTS_ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'projects')
# 注释掉自动创建目录的代码，按用户要求不自动创建目录
# ensure_dir_exists(PROJECTS_ROOT)

class ProjectManager:
    """项目管理类
    
    提供项目的创建、导入、更新、删除等功能
    """
    
    @staticmethod
    def create_project(name, description=None, work_path='/', source_type='zip', source_url=None, 
                      branch='main', git_username=None, git_password=None, tags=None):
        """创建新项目
        
        参数:
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
            dict: 操作结果
        """
        try:
            # 检查项目名称是否已存在
            existing_project = Project.get_or_none(Project.name == name)
            if existing_project:
                return {'success': False, 'message': f'项目名称 {name} 已存在'}
            
            # 创建项目记录
            project = Project.create(
                name=name,
                description=description,
                work_path=work_path,
                source_type=source_type,
                source_url=source_url,
                branch=branch,
                git_username=git_username,
                git_password=git_password,
                status='pending',
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            
            # 处理标签
            if tags:
                ProjectManager._add_tags_to_project(project.id, tags)
            
            # 启动导入线程
            threading.Thread(target=ProjectManager._import_project, args=(project.id,)).start()
            
            return {'success': True, 'message': f'项目 {name} 创建成功，正在导入代码', 'data': {'id': project.id}}
        except Exception as e:
            logger.error(f'创建项目失败: {str(e)}')
            return {'success': False, 'message': f'创建项目失败: {str(e)}'}
    
    @staticmethod
    def update_project(project_id, name=None, description=None, work_path=None, tags=None):
        """更新项目信息
        
        参数:
            project_id: 项目ID
            name: 项目名称
            description: 项目描述
            work_path: 工作路径
            tags: 项目标签列表
            
        返回:
            dict: 操作结果
        """
        try:
            project = Project.get_by_id(project_id)
            
            # 更新项目基本信息
            if name and name != project.name:
                # 检查新名称是否已存在
                existing_project = Project.get_or_none(Project.name == name, Project.id != project_id)
                if existing_project:
                    return {'success': False, 'message': f'项目名称 {name} 已存在'}
                
                # 更新项目文件夹名称
                old_path = os.path.join(PROJECTS_ROOT, project.name)
                new_path = os.path.join(PROJECTS_ROOT, name)
                if os.path.exists(old_path) and os.path.exists(new_path) == False:
                    os.rename(old_path, new_path)
                
                project.name = name
            
            if description is not None:
                project.description = description
            
            if work_path is not None:
                project.work_path = work_path
            
            project.update_time = datetime.now()
            project.save()
            
            # 更新标签
            if tags is not None:
                # 删除现有标签关联
                ProjectToTag.delete().where(ProjectToTag.project == project_id).execute()
                # 添加新标签
                ProjectManager._add_tags_to_project(project_id, tags)
            
            return {'success': True, 'message': '项目更新成功'}
        except Exception as e:
            logger.error(f'更新项目失败: {str(e)}')
            return {'success': False, 'message': f'更新项目失败: {str(e)}'}
    
    @staticmethod
    def delete_project(project_id):
        """删除项目
        
        参数:
            project_id: 项目ID
            
        返回:
            dict: 操作结果
        """
        try:
            project = Project.get_by_id(project_id)
            
            # 删除项目文件夹
            project_path = os.path.join(PROJECTS_ROOT, project.name)
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)
            
            # 删除项目记录和相关标签关联
            with db.atomic():
                ProjectToTag.delete().where(ProjectToTag.project == project_id).execute()
                project.delete_instance()
            
            return {'success': True, 'message': f'项目 {project.name} 删除成功'}
        except Exception as e:
            logger.error(f'删除项目失败: {str(e)}')
            return {'success': False, 'message': f'删除项目失败: {str(e)}'}
    
    @staticmethod
    def get_projects(page=1, per_page=10, search=None, tags=None):
        """获取项目列表
        
        参数:
            page: 页码
            per_page: 每页数量
            search: 搜索关键词
            tags: 标签筛选
            
        返回:
            dict: 项目列表和分页信息
        """
        try:
            query = Project.select()
            
            # 搜索过滤
            if search:
                query = query.where(Project.name.contains(search) | Project.description.contains(search))
            
            # 标签过滤
            if tags:
                tag_ids = [tag.id for tag in ProjectTag.select().where(ProjectTag.name.in_(tags))]
                project_ids = [pt.project.id for pt in ProjectToTag.select().where(ProjectToTag.tag.in_(tag_ids))]
                query = query.where(Project.id.in_(project_ids))
            
            # 排序
            query = query.order_by(Project.update_time.desc())
            
            # 分页
            total = query.count()
            projects = query.paginate(page, per_page)
            
            # 格式化结果
            result = []
            for project in projects:
                project_tags = [tag.name for tag in project.tags]
                result.append({
                    'id': project.id,
                    'name': project.name,
                    'description': project.description,
                    'work_path': project.work_path,
                    'source_type': project.source_type,
                    'status': project.status,
                    'create_time': project.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'update_time': project.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'tags': project_tags
                })
            
            return {
                'success': True,
                'data': {
                    'projects': result,
                    'pagination': {
                        'page': page,
                        'per_page': per_page,
                        'total': total,
                        'pages': (total + per_page - 1) // per_page
                    }
                }
            }
        except Exception as e:
            logger.error(f'获取项目列表失败: {str(e)}')
            return {'success': False, 'message': f'获取项目列表失败: {str(e)}'}
    
    @staticmethod
    def get_project(project_id):
        """获取项目详情
        
        参数:
            project_id: 项目ID
            
        返回:
            dict: 项目详情
        """
        try:
            project = Project.get_by_id(project_id)
            
            # 获取项目标签
            project_tags = [tag.name for tag in project.tags]
            
            # 获取项目文件列表（前100个文件）
            project_path = os.path.join(PROJECTS_ROOT, project.name)
            files = []
            if os.path.exists(project_path):
                for root, dirs, filenames in os.walk(project_path):
                    for filename in filenames:
                        if len(files) < 100:
                            relative_path = os.path.relpath(os.path.join(root, filename), project_path)
                            files.append(relative_path)
                        else:
                            break
                    if len(files) >= 100:
                        break
            
            result = {
                'id': project.id,
                'name': project.name,
                'description': project.description,
                'work_path': project.work_path,
                'source_type': project.source_type,
                'source_url': project.source_url,
                'branch': project.branch,
                'git_username': project.git_username,
                'status': project.status,
                'error_message': project.error_message,
                'create_time': project.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'update_time': project.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                'tags': project_tags,
                'files': files
            }
            
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f'获取项目详情失败: {str(e)}')
            return {'success': False, 'message': f'获取项目详情失败: {str(e)}'}
    
    @staticmethod
    def get_tags():
        """获取所有项目标签
        
        返回:
            list: 标签列表
        """
        try:
            tags = ProjectTag.select().order_by(ProjectTag.name)
            return {'success': True, 'data': [{'id': tag.id, 'name': tag.name} for tag in tags]}
        except Exception as e:
            logger.error(f'获取标签列表失败: {str(e)}')
            return {'success': False, 'message': f'获取标签列表失败: {str(e)}'}
    
    @staticmethod
    def _import_project(project_id):
        """导入项目代码
        
        参数:
            project_id: 项目ID
        """
        try:
            project = Project.get_by_id(project_id)
            project_path = os.path.join(PROJECTS_ROOT, project.name)
            
            # 确保项目目录存在
            ensure_dir_exists(project_path)
            
            if project.source_type == 'zip':
                # ZIP文件导入逻辑
                # 注意：这里只是框架，实际实现需要处理文件上传
                ProjectManager._handle_zip_import(project, project_path)
            elif project.source_type == 'git':
                # Git仓库导入逻辑
                ProjectManager._handle_git_import(project, project_path)
            
            # 尝试自动检测工作路径
            detected_work_path = ProjectManager._detect_work_path(project_path)
            if detected_work_path and project.work_path == '/':
                project.work_path = detected_work_path
                project.save()
            
            # 更新项目状态
            project.status = 'ready'
            project.update_time = datetime.now()
            project.save()
            
        except Exception as e:
            error_msg = f'项目导入失败: {str(e)}'
            logger.error(error_msg)
            # 更新项目状态为失败
            try:
                project = Project.get_by_id(project_id)
                project.status = 'failed'
                project.error_message = str(e)
                project.update_time = datetime.now()
                project.save()
            except:
                pass
    
    @staticmethod
    def _handle_zip_import(project, project_path):
        """处理ZIP文件导入
        
        参数:
            project: 项目对象
            project_path: 项目路径
        """
        # 注意：这里是框架实现，实际需要结合文件上传功能
        # 假设ZIP文件已经上传并保存到临时位置
        # 这里仅作为示例
        pass
    
    @staticmethod
    def _handle_git_import(project, project_path):
        """处理Git仓库导入
        
        参数:
            project: 项目对象
            project_path: 项目路径
        """
        try:
            # 构建Git命令
            git_cmd = ['git', 'clone']
            
            # 如果指定了分支
            if project.branch and project.branch != 'main':
                git_cmd.extend(['-b', project.branch])
            
            # 添加认证信息（如果有）
            repo_url = project.source_url
            if project.git_username and project.git_password:
                # 构建带认证信息的URL
                from urllib.parse import urlparse, urlunparse
                parsed_url = urlparse(repo_url)
                new_netloc = f'{project.git_username}:{project.git_password}@{parsed_url.netloc}'
                repo_url = urlunparse(parsed_url._replace(netloc=new_netloc))
            
            # 添加仓库URL和目标路径
            git_cmd.extend([repo_url, project_path])
            
            # 执行Git克隆命令
            subprocess.run(git_cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        except Exception as e:
            logger.error(f'Git克隆失败: {str(e)}')
            raise
    
    @staticmethod
    def _detect_work_path(project_path):
        """自动检测工作路径
        
        参数:
            project_path: 项目路径
            
        返回:
            str: 检测到的工作路径
        """
        # 检查是否只有一个Python文件
        python_files = list(Path(project_path).glob('*.py'))
        if len(python_files) == 1 and not list(Path(project_path).glob('[!_]*')):
            return '/'  # 单文件情况
        
        # 检查是否有子目录包含Python文件
        subdirs = [d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))]
        for subdir in subdirs:
            subdir_path = os.path.join(project_path, subdir)
            if list(Path(subdir_path).glob('*.py')):
                return f'/{subdir}'  # 子目录情况
        
        return None
    
    @staticmethod
    def _add_tags_to_project(project_id, tags):
        """为项目添加标签
        
        参数:
            project_id: 项目ID
            tags: 标签列表
        """
        for tag_name in tags:
            # 获取或创建标签
            tag, created = ProjectTag.get_or_create(name=tag_name)
            # 添加项目和标签的关联
            ProjectToTag.get_or_create(project=project_id, tag=tag)
    
    @staticmethod
    def upload_project_zip(project_id, zip_file):
        """上传项目ZIP文件
        
        参数:
            project_id: 项目ID
            zip_file: ZIP文件对象
            
        返回:
            dict: 操作结果
        """
        try:
            project = Project.get_by_id(project_id)
            project_path = os.path.join(PROJECTS_ROOT, project.name)
            
            # 创建临时目录保存ZIP文件
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = os.path.join(temp_dir, 'project.zip')
                
                # 保存上传的ZIP文件
                zip_file.save(zip_path)
                
                # 解压ZIP文件到项目目录
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(project_path)
            
            # 自动检测工作路径
            detected_work_path = ProjectManager._detect_work_path(project_path)
            if detected_work_path and project.work_path == '/':
                project.work_path = detected_work_path
                project.save()
            
            return {'success': True, 'message': '项目文件上传成功'}
        except Exception as e:
            logger.error(f'上传项目文件失败: {str(e)}')
            return {'success': False, 'message': f'上传项目文件失败: {str(e)}'}
    
    @staticmethod
    def get_project_file(project_id, file_path):
        """获取项目文件内容
        
        参数:
            project_id: 项目ID
            file_path: 文件路径
            
        返回:
            dict: 文件内容
        """
        try:
            project = Project.get_by_id(project_id)
            full_path = os.path.join(PROJECTS_ROOT, project.name, file_path.lstrip('/'))
            
            # 检查文件是否存在且在项目目录内
            if not os.path.exists(full_path) or not full_path.startswith(PROJECTS_ROOT):
                return {'success': False, 'message': '文件不存在'}
            
            # 读取文件内容
            with open(full_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            return {'success': True, 'data': {'content': content}}
        except UnicodeDecodeError:
            return {'success': False, 'message': '无法读取二进制文件'}
        except Exception as e:
            logger.error(f'读取文件失败: {str(e)}')
            return {'success': False, 'message': f'读取文件失败: {str(e)}'}

# 初始化ProjectManager实例
project_manager = ProjectManager()