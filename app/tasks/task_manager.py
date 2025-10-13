#!/usr/bin/env python3
"""任务管理模块

提供任务的创建、配置、调度和执行功能
"""

import os
import sys
import json
import logging
import threading
import subprocess
import uuid
import time
from datetime import datetime
from pathlib import Path
from app.models.db import db, Task, TaskExecution, TaskLog
from app.utils.tools import ensure_dir_exists
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger

# 配置日志
logger = logging.getLogger(__name__)

# 任务执行实例映射（用于跟踪和管理正在运行的任务）
RUNNING_TASKS = {}
RUNNING_TASKS_LOCK = threading.Lock()

# 任务日志队列（用于实时日志查看）
TASK_LOG_QUEUES = {}
TASK_LOG_QUEUES_LOCK = threading.Lock()

class TaskManager:
    """任务管理器类
    
    负责任务的创建、查询、更新、删除以及调度执行
    """
    
    # 初始化调度器
    def __init__(self):
        """初始化任务管理器和APScheduler调度器"""
        # 创建执行器（支持线程池和进程池）
        self.executors = {
            'default': ThreadPoolExecutor(20),  # 最多20个线程并发执行任务
            'processpool': ProcessPoolExecutor(5)  # 最多5个进程并发执行任务
        }
        
        # 创建调度器
        self.scheduler = BackgroundScheduler(executors=self.executors)
        
        # 启动调度器
        try:
            self.scheduler.start()
            logger.info("任务调度器启动成功")
        except Exception as e:
            logger.error(f"任务调度器启动失败: {str(e)}")
            self.scheduler = None
            
        # 加载所有活跃的任务
        self._load_active_tasks()
    
    def create_task(self, name, description, project_id, python_env_id, command, 
                   schedule_type, schedule_config, max_instances=1):
        """创建新任务
        
        参数:
            name: 任务名称
            description: 任务描述
            project_id: 项目ID（可选）
            python_env_id: Python虚拟环境ID
            command: 执行命令
            schedule_type: 调度类型 (immediate, interval, one-time, cron)
            schedule_config: 调度配置（JSON字符串）
            max_instances: 最大并发实例数
        
        返回:
            dict: 操作结果，包含success和data或message
        """
        try:
            # 验证参数
            if not name or not command or not schedule_type:
                return {'success': False, 'message': '任务名称、执行命令和调度类型为必填项'}
            
            # 验证调度类型
            valid_schedule_types = ['immediate', 'interval', 'one-time', 'cron']
            if schedule_type not in valid_schedule_types:
                return {'success': False, 'message': f'无效的调度类型，可选值: {valid_schedule_types}'}
            
            # 解析调度配置
            try:
                config = json.loads(schedule_config)
            except json.JSONDecodeError:
                return {'success': False, 'message': '调度配置格式无效，必须是JSON字符串'}
            
            # 保存任务到数据库
            with db.atomic():
                task = Task.create(
                    name=name,
                    description=description,
                    project=project_id if project_id else None,
                    python_env=python_env_id,
                    command=command,
                    schedule_type=schedule_type,
                    schedule_config=schedule_config,
                    max_instances=max_instances,
                    update_time=datetime.now()
                )
            
            logger.info(f"创建任务成功: {name} (ID: {task.id})")
            return {'success': True, 'data': {'id': task.id}}
            
        except Exception as e:
            logger.error(f"创建任务失败: {str(e)}")
            return {'success': False, 'message': f'创建任务失败: {str(e)}'}
    
    def get_tasks(self, page=1, per_page=10, search='', project_id=None, python_env_id=None, is_active=None):
        """获取任务列表
        
        参数:
            page: 页码
            per_page: 每页数量
            search: 搜索关键词
            project_id: 项目ID过滤
            python_env_id: Python虚拟环境ID过滤
            is_active: 任务状态过滤
        
        返回:
            dict: 任务列表和分页信息
        """
        try:
            # 构建查询
            query = Task.select()
            
            # 搜索过滤
            if search:
                query = query.where(Task.name.contains(search) | Task.description.contains(search) | Task.command.contains(search))
            
            # 项目过滤
            if project_id is not None:
                query = query.where(Task.project == project_id)
            
            # 环境过滤
            if python_env_id is not None:
                query = query.where(Task.python_env == python_env_id)
            
            # 状态过滤
            if is_active is not None:
                query = query.where(Task.is_active == is_active)
            
            # 排序
            query = query.order_by(Task.update_time.desc())
            
            # 分页
            total = query.count()
            tasks = list(query.paginate(page, per_page))
            
            # 构建返回结果
            data = []
            for task in tasks:
                # 获取下次执行时间
                next_run_time = self.get_next_run_time(task.id)
                
                # 获取运行中的实例数
                running_instances = self.get_running_instances_count(task.id)
                
                data.append({
                    'id': task.id,
                    'name': task.name,
                    'description': task.description,
                    'project_id': task.project.id if task.project else None,
                    'project_name': task.project.name if task.project else None,
                    'python_env_id': task.python_env.id,
                    'python_env_name': task.python_env.name,
                    'command': task.command,
                    'schedule_type': task.schedule_type,
                    'schedule_config': task.schedule_config,
                    'max_instances': task.max_instances,
                    'is_active': task.is_active,
                    'next_run_time': next_run_time,
                    'running_instances': running_instances,
                    'create_time': task.create_time.isoformat(),
                    'update_time': task.update_time.isoformat()
                })
            
            return {
                'success': True,
                'data': data,
                'pagination': {
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"获取任务列表失败: {str(e)}")
            return {'success': False, 'message': f'获取任务列表失败: {str(e)}'}
    
    def get_task(self, task_id):
        """获取任务详情
        
        参数:
            task_id: 任务ID
        
        返回:
            dict: 任务详情
        """
        try:
            # 获取任务
            task = Task.get_or_none(Task.id == task_id)
            
            if not task:
                return {'success': False, 'message': '任务不存在'}
            
            # 获取下次执行时间
            next_run_time = self.get_next_run_time(task.id)
            
            # 构建返回结果
            data = {
                'id': task.id,
                'name': task.name,
                'description': task.description,
                'project_id': task.project.id if task.project else None,
                'project_name': task.project.name if task.project else None,
                'python_env_id': task.python_env.id,
                'python_env_name': task.python_env.name,
                'command': task.command,
                'schedule_type': task.schedule_type,
                'schedule_config': task.schedule_config,
                'max_instances': task.max_instances,
                'is_active': task.is_active,
                'next_run_time': next_run_time,
                'create_time': task.create_time.isoformat(),
                'update_time': task.update_time.isoformat()
            }
            
            return {'success': True, 'data': data}
            
        except Exception as e:
            logger.error(f"获取任务详情失败: {str(e)}")
            return {'success': False, 'message': f'获取任务详情失败: {str(e)}'}
    
    def update_task(self, task_id, **kwargs):
        """更新任务信息
        
        参数:
            task_id: 任务ID
            **kwargs: 要更新的字段
        
        返回:
            dict: 操作结果
        """
        try:
            # 获取任务
            task = Task.get_or_none(Task.id == task_id)
            
            if not task:
                return {'success': False, 'message': '任务不存在'}
            
            # 验证调度配置（如果提供）
            if 'schedule_config' in kwargs:
                try:
                    json.loads(kwargs['schedule_config'])
                except json.JSONDecodeError:
                    return {'success': False, 'message': '调度配置格式无效，必须是JSON字符串'}
            
            # 验证调度类型（如果提供）
            if 'schedule_type' in kwargs:
                valid_schedule_types = ['immediate', 'interval', 'one-time', 'cron']
                if kwargs['schedule_type'] not in valid_schedule_types:
                    return {'success': False, 'message': f'无效的调度类型，可选值: {valid_schedule_types}'}
            
            # 如果任务正在运行，先暂停
            was_active = task.is_active
            if was_active:
                self.pause_task(task_id)
            
            # 更新任务
            with db.atomic():
                update_data = {k: v for k, v in kwargs.items() if k in Task._meta.fields}
                update_data['update_time'] = datetime.now()
                Task.update(**update_data).where(Task.id == task_id).execute()
            
            # 如果之前是活跃的，重新启动
            if was_active and ('is_active' not in kwargs or kwargs['is_active']):
                self.start_task(task_id)
            
            logger.info(f"更新任务成功: {task_id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"更新任务失败: {str(e)}")
            return {'success': False, 'message': f'更新任务失败: {str(e)}'}
    
    def delete_task(self, task_id):
        """删除任务
        
        参数:
            task_id: 任务ID
        
        返回:
            dict: 操作结果
        """
        try:
            # 获取任务
            task = Task.get_or_none(Task.id == task_id)
            
            if not task:
                return {'success': False, 'message': '任务不存在'}
            
            # 暂停任务
            self.pause_task(task_id)
            
            # 删除任务
            with db.atomic():
                # 级联删除相关记录
                TaskExecution.delete().where(TaskExecution.task == task_id).execute()
                Task.delete().where(Task.id == task_id).execute()
            
            logger.info(f"删除任务成功: {task_id}")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"删除任务失败: {str(e)}")
            return {'success': False, 'message': f'删除任务失败: {str(e)}'}
    
    def start_task(self, task_id):
        """启动任务调度
        
        参数:
            task_id: 任务ID
        
        返回:
            dict: 操作结果
        """
        try:
            # 获取任务
            task = Task.get_or_none(Task.id == task_id)
            
            if not task:
                return {'success': False, 'message': '任务不存在'}
            
            # 如果调度器未初始化，先初始化
            if not self.scheduler or not self.scheduler.running:
                self.__init__()
                if not self.scheduler or not self.scheduler.running:
                    return {'success': False, 'message': '调度器初始化失败'}
            
            # 先移除可能存在的任务
            self.scheduler.remove_job(str(task_id))
            
            # 解析调度配置
            schedule_config = json.loads(task.schedule_config)
            
            # 根据调度类型创建触发器
            if task.schedule_type == 'immediate':
                # 立即执行任务
                self.execute_task(task_id)
                
            elif task.schedule_type == 'interval':
                # 间隔执行
                trigger = IntervalTrigger(
                    seconds=schedule_config.get('seconds', 0),
                    minutes=schedule_config.get('minutes', 0),
                    hours=schedule_config.get('hours', 0),
                    days=schedule_config.get('days', 0)
                )
                
                # 添加任务到调度器
                self.scheduler.add_job(
                    self.execute_task,
                    trigger,
                    args=[task_id],
                    id=str(task_id),
                    max_instances=task.max_instances,
                    replace_existing=True
                )
                
            elif task.schedule_type == 'one-time':
                # 一次性执行
                run_date = datetime.strptime(schedule_config.get('run_date'), '%Y-%m-%d %H:%M:%S')
                trigger = DateTrigger(run_date=run_date)
                
                # 添加任务到调度器
                self.scheduler.add_job(
                    self.execute_task,
                    trigger,
                    args=[task_id],
                    id=str(task_id),
                    max_instances=task.max_instances,
                    replace_existing=True
                )
                
            elif task.schedule_type == 'cron':
                # Cron表达式执行
                trigger = CronTrigger(
                    minute=schedule_config.get('minute', '*'),
                    hour=schedule_config.get('hour', '*'),
                    day=schedule_config.get('day', '*'),
                    month=schedule_config.get('month', '*'),
                    day_of_week=schedule_config.get('day_of_week', '*')
                )
                
                # 添加任务到调度器
                self.scheduler.add_job(
                    self.execute_task,
                    trigger,
                    args=[task_id],
                    id=str(task_id),
                    max_instances=task.max_instances,
                    replace_existing=True
                )
            
            # 更新任务状态
            with db.atomic():
                Task.update(is_active=True, update_time=datetime.now()).where(Task.id == task_id).execute()
            
            logger.info(f"启动任务成功: {task_id} ({task.name})")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"启动任务失败: {str(e)}")
            return {'success': False, 'message': f'启动任务失败: {str(e)}'}
    
    def pause_task(self, task_id):
        """暂停任务调度
        
        参数:
            task_id: 任务ID
        
        返回:
            dict: 操作结果
        """
        try:
            # 获取任务
            task = Task.get_or_none(Task.id == task_id)
            
            if not task:
                return {'success': False, 'message': '任务不存在'}
            
            # 移除调度器中的任务
            if self.scheduler and self.scheduler.running:
                try:
                    self.scheduler.remove_job(str(task_id))
                except:
                    pass  # 忽略任务不存在的异常
            
            # 更新任务状态
            with db.atomic():
                Task.update(is_active=False, update_time=datetime.now()).where(Task.id == task_id).execute()
            
            logger.info(f"暂停任务成功: {task_id} ({task.name})")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"暂停任务失败: {str(e)}")
            return {'success': False, 'message': f'暂停任务失败: {str(e)}'}
    
    def execute_task(self, task_id):
        """执行任务
        
        参数:
            task_id: 任务ID
        """
        try:
            # 获取任务
            task = Task.get_or_none(Task.id == task_id)
            
            if not task:
                logger.error(f"执行任务失败: 任务不存在 ({task_id})")
                return
            
            # 创建执行记录
            with db.atomic():
                execution = TaskExecution.create(
                    task=task,
                    status='running'
                )
            
            # 记录开始日志
            self._log_task_execution(execution.id, 'INFO', f'任务开始执行: {task.name}')
            self._log_task_execution(execution.id, 'INFO', f'执行命令: {task.command}')
            
            # 启动执行线程
            thread = threading.Thread(
                target=self._run_task_in_thread, 
                args=(task_id, execution.id)
            )
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"执行任务时发生错误: {str(e)}")
    
    def _run_task_in_thread(self, task_id, execution_id):
        """在线程中运行任务
        
        参数:
            task_id: 任务ID
            execution_id: 执行记录ID
        """
        try:
            # 获取任务和执行记录
            task = Task.get_or_none(Task.id == task_id)
            execution = TaskExecution.get_or_none(TaskExecution.id == execution_id)
            
            if not task or not execution:
                return
            
            # 获取虚拟环境路径
            venv_path = task.python_env.path
            
            # 构建命令执行环境
            env = os.environ.copy()
            env['PATH'] = f"{venv_path}/bin:{env['PATH']}"
            
            # 确定工作目录（如果有项目）
            cwd = None
            if task.project:
                project_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'projects', str(task.project.id))
                if os.path.exists(project_path):
                    cwd = project_path
                    self._log_task_execution(execution_id, 'INFO', f'工作目录: {cwd}')
            
            # 执行命令
            process = subprocess.Popen(
                task.command, 
                shell=True, 
                env=env, 
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 记录运行中的任务
            with RUNNING_TASKS_LOCK:
                RUNNING_TASKS[execution_id] = {
                    'process': process,
                    'task_id': task_id,
                    'start_time': datetime.now()
                }
            
            # 初始化日志队列
            log_queue_id = f"task_{task_id}_{execution_id}"
            with TASK_LOG_QUEUES_LOCK:
                TASK_LOG_QUEUES[log_queue_id] = []
            
            # 实时获取输出并记录日志
            def read_stream(stream, level):
                while True:
                    line = stream.readline()
                    if not line:
                        break
                    self._log_task_execution(execution_id, level, line.strip())
            
            # 分别读取标准输出和标准错误
            stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, 'INFO'))
            stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, 'ERROR'))
            
            stdout_thread.daemon = True
            stderr_thread.daemon = True
            
            stdout_thread.start()
            stderr_thread.start()
            
            # 等待进程完成
            try:
                # 检查任务是否被终止
                while process.poll() is None:
                    with RUNNING_TASKS_LOCK:
                        if execution_id not in RUNNING_TASKS:
                            process.terminate()
                            break
                    time.sleep(0.5)
                
                # 等待输出线程完成
                stdout_thread.join(timeout=1)
                stderr_thread.join(timeout=1)
                
                # 检查执行状态
                if process.returncode == 0:
                    status = 'completed'
                    self._log_task_execution(execution_id, 'INFO', f'任务执行成功: {task.name}')
                else:
                    status = 'failed'
                    error_message = f'命令执行失败，返回码: {process.returncode}'
                    self._log_task_execution(execution_id, 'ERROR', error_message)
                    
            except Exception as e:
                status = 'failed'
                error_message = f'任务执行异常: {str(e)}'
                self._log_task_execution(execution_id, 'ERROR', error_message)
                
            # 更新执行记录
            end_time = datetime.now()
            duration = (end_time - execution.start_time).total_seconds()
            
            with db.atomic():
                TaskExecution.update(
                    end_time=end_time,
                    status=status,
                    duration=duration,
                    error_message=error_message if status == 'failed' else None
                ).where(TaskExecution.id == execution.id).execute()
                
            # 从运行任务映射中移除
            with RUNNING_TASKS_LOCK:
                if execution_id in RUNNING_TASKS:
                    del RUNNING_TASKS[execution_id]
                    
        except Exception as e:
            # 记录异常
            error_message = str(e)
            self._log_task_execution(execution_id, 'ERROR', f'任务执行异常: {error_message}')
            
            # 更新执行记录
            try:
                execution = TaskExecution.get_or_none(TaskExecution.id == execution_id)
                if execution:
                    end_time = datetime.now()
                    duration = (end_time - execution.start_time).total_seconds() if execution.start_time else None
                    
                    with db.atomic():
                        TaskExecution.update(
                            end_time=end_time,
                            status='failed',
                            duration=duration,
                            error_message=error_message
                        ).where(TaskExecution.id == execution.id).execute()
            except:
                pass
            
            # 从运行任务映射中移除
            with RUNNING_TASKS_LOCK:
                if execution_id in RUNNING_TASKS:
                    del RUNNING_TASKS[execution_id]
    
    def _log_task_execution(self, execution_id, level, message):
        """记录任务执行日志
        
        参数:
            execution_id: 执行记录ID
            level: 日志级别
            message: 日志消息
        """
        try:
            # 获取执行记录，用于获取任务ID
            execution = TaskExecution.get_or_none(TaskExecution.id == execution_id)
            if not execution:
                return
            
            # 分割长消息，避免数据库限制
            max_length = 2000
            messages = [message[i:i+max_length] for i in range(0, len(message), max_length)]
            
            with db.atomic():
                for msg in messages:
                    TaskLog.create(
                        execution=execution_id,
                        level=level,
                        message=msg,
                        create_time=datetime.now()
                    )
            
            # 添加到日志队列（用于实时日志查看）
            log_queue_id = f"task_{execution.task.id}_{execution_id}"
            with TASK_LOG_QUEUES_LOCK:
                if log_queue_id in TASK_LOG_QUEUES:
                    timestamp = datetime.now().isoformat()
                    log_entry = {
                        'timestamp': timestamp,
                        'level': level,
                        'message': message
                    }
                    TASK_LOG_QUEUES[log_queue_id].append(log_entry)
                    
                    # 限制队列大小，防止内存溢出
                    if len(TASK_LOG_QUEUES[log_queue_id]) > 1000:
                        TASK_LOG_QUEUES[log_queue_id] = TASK_LOG_QUEUES[log_queue_id][-1000:]
            
        except Exception as e:
            logger.error(f"记录任务日志失败: {str(e)}")
    
    def terminate_task_execution(self, execution_id):
        """强制终止正在运行的任务执行实例
        
        参数:
            execution_id: 执行记录ID
            
        返回:
            dict: 操作结果
        """
        try:
            # 检查执行记录是否存在
            execution = TaskExecution.get_or_none(TaskExecution.id == execution_id)
            if not execution:
                return {'success': False, 'message': '执行记录不存在'}
            
            # 检查任务是否正在运行
            with RUNNING_TASKS_LOCK:
                if execution_id not in RUNNING_TASKS:
                    return {'success': False, 'message': '任务不在运行中'}
                
                # 获取进程对象
                process_info = RUNNING_TASKS[execution_id]
                process = process_info['process']
                
                # 记录终止日志
                self._log_task_execution(execution_id, 'WARN', '任务正在被强制终止...')
                
                # 终止进程
                try:
                    # 先尝试正常终止
                    process.terminate()
                    # 等待最多5秒
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # 如果超时，强制终止
                        process.kill()
                        self._log_task_execution(execution_id, 'ERROR', '任务强制终止超时，已强制杀死进程')
                    else:
                        self._log_task_execution(execution_id, 'INFO', '任务已被成功终止')
                except Exception as e:
                    self._log_task_execution(execution_id, 'ERROR', f'终止任务失败: {str(e)}')
                    return {'success': False, 'message': f'终止任务失败: {str(e)}'}
                
                # 从运行任务映射中移除
                del RUNNING_TASKS[execution_id]
            
            # 更新执行记录
            end_time = datetime.now()
            duration = (end_time - execution.start_time).total_seconds()
            
            with db.atomic():
                TaskExecution.update(
                    end_time=end_time,
                    status='terminated',
                    duration=duration,
                    error_message='任务被用户强制终止'
                ).where(TaskExecution.id == execution_id).execute()
                
            return {'success': True, 'message': '任务已成功终止'}
            
        except Exception as e:
            logger.error(f"强制终止任务时发生错误: {str(e)}")
            return {'success': False, 'message': f'终止任务时发生错误: {str(e)}'}
    
    def get_running_instances_count(self, task_id):
        """获取任务正在运行的实例数
        
        参数:
            task_id: 任务ID
            
        返回:
            int: 运行中的实例数
        """
        count = 0
        with RUNNING_TASKS_LOCK:
            for execution_id, info in RUNNING_TASKS.items():
                if info['task_id'] == task_id:
                    count += 1
        return count
    
    def get_task_execution_stats(self, task_id):
        """获取任务执行统计信息
        
        参数:
            task_id: 任务ID
            
        返回:
            dict: 执行统计信息
        """
        try:
            # 验证任务是否存在
            task = Task.get_or_none(Task.id == task_id)
            if not task:
                return {}
            
            # 获取执行记录
            executions = TaskExecution.select().where(TaskExecution.task == task_id)
            
            # 计算统计数据
            total = executions.count()
            completed = executions.where(TaskExecution.status == 'completed').count()
            failed = executions.where(TaskExecution.status == 'failed').count()
            terminated = executions.where(TaskExecution.status == 'terminated').count()
            
            # 计算平均执行时间
            durations = [e.duration for e in executions if e.duration and e.status == 'completed']
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            # 获取最近执行状态
            last_execution = executions.order_by(TaskExecution.start_time.desc()).first()
            last_status = last_execution.status if last_execution else None
            last_execution_time = last_execution.start_time.isoformat() if last_execution else None
            
            return {
                'total_executions': total,
                'completed': completed,
                'failed': failed,
                'terminated': terminated,
                'average_duration': avg_duration,
                'last_execution_status': last_status,
                'last_execution_time': last_execution_time
            }
            
        except Exception as e:
            logger.error(f"获取任务执行统计时发生错误: {str(e)}")
            return {}
    
    def _load_active_tasks(self):
        """加载所有活跃的任务到调度器"""
        try:
            # 获取所有活跃的任务
            active_tasks = Task.select().where(Task.is_active == True)
            
            for task in active_tasks:
                try:
                    # 尝试启动任务调度
                    self.start_task(task.id)
                except Exception as e:
                    logger.error(f"加载任务 {task.name} 失败: {str(e)}")
                    # 标记任务为非活跃状态
                    with db.atomic():
                        Task.update(is_active=False).where(Task.id == task.id).execute()
        except Exception as e:
            logger.error(f"加载活跃任务时发生错误: {str(e)}")
    
    def get_realtime_logs(self, task_id, execution_id, last_timestamp=None, limit=100):
        """获取实时日志（不查询数据库，从内存队列中获取）
        
        参数:
            task_id: 任务ID
            execution_id: 执行记录ID
            last_timestamp: 上次获取的最后一条日志的时间戳
            limit: 最多获取的日志条数
            
        返回:
            list: 日志条目列表
        """
        try:
            log_queue_id = f"task_{task_id}_{execution_id}"
            logs = []
            
            with TASK_LOG_QUEUES_LOCK:
                if log_queue_id in TASK_LOG_QUEUES:
                    # 过滤出最新的日志
                    if last_timestamp:
                        logs = [log for log in TASK_LOG_QUEUES[log_queue_id] if log['timestamp'] > last_timestamp]
                    else:
                        logs = TASK_LOG_QUEUES[log_queue_id][-limit:]
                    
            return {'success': True, 'logs': logs}
            
        except Exception as e:
            logger.error(f"获取实时日志时发生错误: {str(e)}")
            return {'success': False, 'message': f'获取实时日志失败: {str(e)}'}
    
    def get_task_executions(self, task_id, page=1, per_page=10, status=None):
        """获取任务执行历史记录
        
        参数:
            task_id: 任务ID
            page: 页码
            per_page: 每页数量
            status: 执行状态过滤
        
        返回:
            dict: 执行历史记录
        """
        try:
            # 验证任务是否存在
            task = Task.get_or_none(Task.id == task_id)
            if not task:
                return {'success': False, 'message': '任务不存在'}
            
            # 构建查询
            query = TaskExecution.select().where(TaskExecution.task == task_id)
            
            # 状态过滤
            if status:
                query = query.where(TaskExecution.status == status)
            
            # 排序
            query = query.order_by(TaskExecution.start_time.desc())
            
            # 分页
            total = query.count()
            executions = list(query.paginate(page, per_page))
            
            # 构建返回结果
            data = []
            for execution in executions:
                # 检查是否正在运行
                is_running = False
                with RUNNING_TASKS_LOCK:
                    if execution.id in RUNNING_TASKS:
                        is_running = True
                        execution.status = 'running'
                
                data.append({
                    'id': execution.id,
                    'start_time': execution.start_time.isoformat(),
                    'end_time': execution.end_time.isoformat() if execution.end_time else None,
                    'status': execution.status,
                    'duration': execution.duration if execution.duration else None,
                    'error_message': execution.error_message,
                    'is_running': is_running
                })
            
            return {
                'success': True,
                'data': data,
                'pagination': {
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"获取任务执行历史失败: {str(e)}")
            return {'success': False, 'message': f'获取任务执行历史失败: {str(e)}'}
    
    def get_task_logs(self, execution_id, page=1, per_page=50, level=None, search=''):
        """获取任务执行日志
        
        参数:
            execution_id: 执行记录ID
            page: 页码
            per_page: 每页数量
            level: 日志级别过滤
            search: 关键词搜索
        
        返回:
            dict: 执行日志
        """
        try:
            # 验证执行记录是否存在
            execution = TaskExecution.get_or_none(TaskExecution.id == execution_id)
            if not execution:
                return {'success': False, 'message': '执行记录不存在'}
            
            # 构建查询
            query = TaskLog.select().where(TaskLog.execution == execution_id)
            
            # 级别过滤
            if level:
                query = query.where(TaskLog.level == level)
            
            # 关键词搜索
            if search:
                query = query.where(TaskLog.message.contains(search))
            
            # 排序
            query = query.order_by(TaskLog.timestamp)
            
            # 分页
            total = query.count()
            logs = list(query.paginate(page, per_page))
            
            # 构建返回结果
            data = []
            for log in logs:
                data.append({
                    'id': log.id,
                    'timestamp': log.timestamp.isoformat(),
                    'level': log.level,
                    'message': log.message
                })
            
            return {
                'success': True,
                'data': data,
                'pagination': {
                    'total': total,
                    'page': page,
                    'per_page': per_page,
                    'total_pages': (total + per_page - 1) // per_page
                }
            }
            
        except Exception as e:
            logger.error(f"获取任务执行日志失败: {str(e)}")
            return {'success': False, 'message': f'获取任务执行日志失败: {str(e)}'}
    
    def get_next_run_time(self, task_id):
        """获取任务下次执行时间
        
        参数:
            task_id: 任务ID
        
        返回:
            str: 下次执行时间（ISO格式）或None
        """
        try:
            if not self.scheduler or not self.scheduler.running:
                return None
            
            # 检查任务是否在调度器中
            jobs = self.scheduler.get_jobs(job_id=str(task_id))
            if not jobs:
                return None
            
            # 获取下次执行时间
            next_run_time = jobs[0].next_run_time
            if next_run_time:
                return next_run_time.isoformat()
            
            return None
            
        except Exception as e:
            logger.error(f"获取下次执行时间失败: {str(e)}")
            return None
    
    def shutdown(self):
        """关闭调度器"""
        if self.scheduler and self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("任务调度器已关闭")

# 创建全局任务管理器实例
task_manager = TaskManager()