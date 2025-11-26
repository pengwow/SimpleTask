#!/usr/bin/env python3
"""项目管理模块

提供项目的创建、配置、导入和管理功能
"""

import os
import sys
import json
import shutil
import logging
import threading
import subprocess
import tempfile
import zipfile
import requests
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from app.db import get_db, Project
# 导入工具函数
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
            db = next(get_db())
            try:
                existing_project = db.query(Project).filter(Project.name == name).first()
                if existing_project:
                    return {'success': False, 'message': f'项目名称 {name} 已存在'}
                
                # 创建项目记录
                project = Project(
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
                    update_time=datetime.now(),
                    tags=json.dumps(tags or [])
                )
                db.add(project)
                db.commit()
                db.refresh(project)
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
            
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
            db = next(get_db())
            # 获取项目
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {'success': False, 'message': '项目不存在'}
            
            # 更新项目基本信息
            if name and name != project.name:
                # 检查新名称是否已存在
                existing_project = db.query(Project).filter(Project.name == name, Project.id != project_id).first()
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
            
            # 更新标签
            if tags is not None:
                project.tags = json.dumps(tags)
            
            project.update_time = datetime.now()
            db.commit()
            
            return {'success': True, 'message': '项目更新成功'}
        except Exception as e:
            if 'db' in locals():
                db.rollback()
            logger.error(f'更新项目失败: {str(e)}')
            return {'success': False, 'message': f'更新项目失败: {str(e)}'}
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def delete_project(project_id):
        """删除项目
        
        参数:
            project_id: 项目ID
            
        返回:
            dict: 操作结果
        """
        try:
            # 导入模块以获取当前的PROJECTS_ROOT值
            import app.projects.project_manager as pm_module
            db = next(get_db())
            # 获取项目
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {'success': False, 'message': '项目不存在'}
            
            # 删除项目文件夹
            project_path = os.path.join(pm_module.PROJECTS_ROOT, project.name)
            if os.path.exists(project_path):
                shutil.rmtree(project_path, ignore_errors=True)
            
            # 删除项目记录
            db.delete(project)
            db.commit()
            
            return {'success': True, 'message': f'项目 {project.name} 删除成功'}
        except Exception as e:
            if 'db' in locals():
                db.rollback()
            logger.error(f'删除项目失败: {str(e)}')
            return {'success': False, 'message': f'删除项目失败: {str(e)}'}
        finally:
            if 'db' in locals():
                db.close()
    
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
            # 构建查询
            db = next(get_db())
            # 获取查询对象
            query = db.query(Project)
            
            # 搜索过滤
            if search:
                from sqlalchemy import or_
                query = query.filter(
                    or_(
                        Project.name.contains(search),
                        Project.description.contains(search)
                    )
                )
                
            # 排序
            from sqlalchemy import desc
            query = query.order_by(desc(Project.update_time))
            
            # 分页
            total = query.count()
            projects = query.offset((page - 1) * per_page).limit(per_page).all()
            
            # 格式化结果
            result = []
            for project in projects:
                # 解析标签JSON字符串为列表
                project_tags = json.loads(project.tags) if project.tags else []
                
                # 标签过滤
                if tags:
                    if not any(tag in project_tags for tag in tags):
                        continue
                
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
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def get_project(project_id):
        """获取项目详情
        
        参数:
            project_id: 项目ID
            
        返回:
            dict: 项目详情
        """
        try:
            db = next(get_db())
            # 获取项目
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {'success': False, 'message': '项目不存在'}
            
            # 解析标签JSON字符串为列表
            project_tags = json.loads(project.tags) if project.tags else []
            
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
                'status': project.status,
                'create_time': project.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'update_time': project.update_time.strftime('%Y-%m-%d %H:%M:%S'),
                'files': files,
                'tags': project_tags
            }
            
            return {'success': True, 'data': result}
        except Exception as e:
            logger.error(f'获取项目详情失败: {str(e)}')
            return {'success': False, 'message': f'获取项目详情失败: {str(e)}'}
        finally:
            if 'db' in locals():
                db.close()
    
    @staticmethod
    def get_tags():
        """获取所有项目标签
        
        返回:
            list: 标签列表
        """
        try:
            db = next(get_db())
            try:
                # 获取所有项目的标签
                projects = db.query(Project).all()
                tag_set = set()
                
                for project in projects:
                    if project.tags:
                        project_tags = json.loads(project.tags)
                        tag_set.update(project_tags)
                
                # 转换为列表并排序
                tags = sorted(list(tag_set))
                # 构造返回格式
                return {'success': True, 'data': [{'name': tag} for tag in tags]}
            finally:
                db.close()
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
            db = next(get_db())
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return
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
            
            # 更新项目状态
            project.status = 'ready'
            project.update_time = datetime.now()
            db.commit()
            
        except Exception as e:
            error_msg = f'项目导入失败: {str(e)}'
            logger.error(error_msg)
            # 更新项目状态为失败
            try:
                db = next(get_db())
                project = db.query(Project).filter(Project.id == project_id).first()
                if project:
                    project.status = 'failed'
                    project.error_message = str(e)
                    project.update_time = datetime.now()
                    db.commit()
            except:
                pass
        finally:
            if 'db' in locals():
                db.close()
    
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
        # 先检查是否有子目录包含Python文件
        subdirs = [d for d in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, d))]
        for subdir in subdirs:
            subdir_path = os.path.join(project_path, subdir)
            if list(Path(subdir_path).glob('*.py')):
                return f'/{subdir}'  # 子目录情况
        
        # 检查是否有根目录的Python文件
        python_files = list(Path(project_path).glob('*.py'))
        if len(python_files) >= 1:
            return '/'  # 单文件情况
        
        return '/'  # 默认返回根目录
    
    @staticmethod
    def _add_tags_to_project(project_id, tags, db=None):
        """为项目添加标签
        
        参数:
            project_id: 项目ID
            tags: 标签列表
            db: 数据库会话（如果外部提供）
        """
        need_close = False
        if db is None:
            db = next(get_db())
            need_close = True
        
        try:
            for tag_name in tags:
                # 获取或创建标签
                tag = db.query(ProjectTag).filter(ProjectTag.name == tag_name).first()
                if not tag:
                    tag = ProjectTag(name=tag_name)
                    db.add(tag)
                    db.commit()
                    db.refresh(tag)
                
                # 添加项目和标签的关联
                existing = db.query(ProjectToTag).filter(
                    ProjectToTag.project_id == project_id,
                    ProjectToTag.tag_id == tag.id
                ).first()
                if not existing:
                    project_tag = ProjectToTag(project_id=project_id, tag_id=tag.id)
                    db.add(project_tag)
            
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            if need_close:
                db.close()
    
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
            db = next(get_db())
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {'success': False, 'message': '项目不存在'}
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
                db.commit()
            
            return {'success': True, 'message': '项目文件上传成功'}
        except Exception as e:
            if 'db' in locals():
                db.rollback()
            logger.error(f'上传项目文件失败: {str(e)}')
            return {'success': False, 'message': f'上传项目文件失败: {str(e)}'}
        finally:
            if 'db' in locals():
                db.close()
    
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
            db = next(get_db())
            project = db.query(Project).filter(Project.id == project_id).first()
            if not project:
                return {'success': False, 'message': '项目不存在'}
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
        finally:
            if 'db' in locals():
                db.close()

# 初始化ProjectManager实例
project_manager = ProjectManager()