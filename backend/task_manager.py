import os
import sys
import json
import time
import logging
import datetime
import threading
from typing import Dict, List, Optional, Any, Union

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor, ProcessPoolExecutor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("task_manager.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TaskManager")


class TaskModel:
    """任务模型，定义任务的基本属性和方法"""
    def __init__(self, task_id: str, name: str, project_id: str, python_env: str,
                 command: str, schedule_type: str, schedule_config: Dict, 
                 description: str = "", max_instances: int = 1, tags: List[str] = None,
                 status: str = "active"):
        """初始化任务模型
        
        参数:
            task_id: 任务唯一标识
            name: 任务名称
            project_id: 所属项目ID
            python_env: Python虚拟环境
            command: 执行命令
            schedule_type: 调度类型 (immediate, interval, one-time, cron)
            schedule_config: 调度配置，根据调度类型不同而不同
            description: 任务描述
            max_instances: 最大并发实例数
            tags: 任务标签列表
            status: 任务状态 (active, paused, error)
        """
        self.task_id = task_id
        self.name = name
        self.project_id = project_id
        self.python_env = python_env
        self.command = command
        self.schedule_type = schedule_type
        self.schedule_config = schedule_config
        self.description = description
        self.max_instances = max_instances
        self.tags = tags or []
        self.status = status
        self.created_at = datetime.datetime.now()
        self.updated_at = datetime.datetime.now()
        
        # APScheduler相关属性
        self.job_id = f"task_{task_id}"
    
    def to_dict(self) -> Dict:
        """将任务模型转换为字典格式"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "project_id": self.project_id,
            "python_env": self.python_env,
            "command": self.command,
            "schedule_type": self.schedule_type,
            "schedule_config": self.schedule_config,
            "description": self.description,
            "max_instances": self.max_instances,
            "tags": self.tags,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TaskModel':
        """从字典创建任务模型"""
        task = cls(
            task_id=data["task_id"],
            name=data["name"],
            project_id=data["project_id"],
            python_env=data["python_env"],
            command=data["command"],
            schedule_type=data["schedule_type"],
            schedule_config=data["schedule_config"],
            description=data.get("description", ""),
            max_instances=data.get("max_instances", 1),
            tags=data.get("tags", []),
            status=data.get("status", "active")
        )
        # 恢复时间戳
        if "created_at" in data:
            task.created_at = datetime.datetime.fromisoformat(data["created_at"])
        if "updated_at" in data:
            task.updated_at = datetime.datetime.fromisoformat(data["updated_at"])
        return task


class ExecutionHistory:
    """任务执行历史记录"""
    def __init__(self, execution_id: str, task_id: str, start_time: datetime.datetime,
                 end_time: Optional[datetime.datetime] = None, status: str = "running",
                 duration: Optional[float] = None, error_message: Optional[str] = None):
        """初始化执行历史记录
        
        参数:
            execution_id: 执行实例唯一标识
            task_id: 任务ID
            start_time: 开始时间
            end_time: 结束时间
            status: 执行状态 (running, success, failed)
            duration: 执行时长（秒）
            error_message: 错误信息
        """
        self.execution_id = execution_id
        self.task_id = task_id
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.duration = duration
        self.error_message = error_message
    
    def to_dict(self) -> Dict:
        """将执行历史记录转换为字典格式"""
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "duration": self.duration,
            "error_message": self.error_message
        }


class TaskLogger:
    """任务日志记录器"""
    def __init__(self, log_dir: str = "./logs"):
        """初始化任务日志记录器
        
        参数:
            log_dir: 日志存储目录
        """
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
    
    def write_log(self, execution_id: str, message: str, level: str = "INFO") -> None:
        """写入日志
        
        参数:
            execution_id: 执行实例ID
            message: 日志消息
            level: 日志级别
        """
        log_file = os.path.join(self.log_dir, f"{execution_id}.log")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def read_logs(self, execution_id: str, start_time: Optional[datetime.datetime] = None,
                 end_time: Optional[datetime.datetime] = None, level: Optional[str] = None,
                 keyword: Optional[str] = None) -> List[str]:
        """读取日志
        
        参数:
            execution_id: 执行实例ID
            start_time: 开始时间
            end_time: 结束时间
            level: 日志级别
            keyword: 关键字
        
        返回:
            List[str]: 日志条目列表
        """
        log_file = os.path.join(self.log_dir, f"{execution_id}.log")
        logs = []
        
        if not os.path.exists(log_file):
            return logs
        
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                # 解析时间戳和日志级别
                if line.startswith("["):
                    try:
                        timestamp_str = line[1:20]  # 格式: 2025-10-11 10:30:00
                        log_timestamp = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                        
                        # 时间范围过滤
                        if start_time and log_timestamp < start_time:
                            continue
                        if end_time and log_timestamp > end_time:
                            continue
                        
                        # 日志级别过滤
                        if level:
                            level_pos = line.find("] ") + 2
                            log_level = line[level_pos:level_pos + len(level)]
                            if log_level != level:
                                continue
                        
                        # 关键字过滤
                        if keyword and keyword not in line:
                            continue
                        
                        logs.append(line.strip())
                    except Exception:
                        # 格式不匹配的行直接跳过
                        continue
        
        return logs
    
    def download_logs(self, execution_id: str) -> str:
        """下载日志文件路径
        
        参数:
            execution_id: 执行实例ID
        
        返回:
            str: 日志文件路径
        """
        return os.path.join(self.log_dir, f"{execution_id}.log")


class TaskManager:
    """任务管理器，负责任务的创建、删除、修改、查询和调度"""
    def __init__(self, db_path: str = "./task_manager.db"):
        """初始化任务管理器
        
        参数:
            db_path: 数据库文件路径
        """
        # 初始化APScheduler
        self.scheduler = BackgroundScheduler(jobstores={
            'default': SQLAlchemyJobStore(url=f'sqlite:///{db_path}'),
            'memory': MemoryJobStore()
        }, executors={
            'default': ThreadPoolExecutor(20),
            'processpool': ProcessPoolExecutor(5)
        }, job_defaults={
            'coalesce': True,
            'max_instances': 1
        })
        
        # 启动调度器
        try:
            self.scheduler.start()
            logger.info("调度器启动成功")
        except Exception as e:
            logger.error(f"调度器启动失败: {str(e)}")
            raise
        
        # 初始化任务存储和执行历史
        self.tasks: Dict[str, TaskModel] = {}
        self.execution_history: Dict[str, List[ExecutionHistory]] = {}
        self.current_executions: Dict[str, ExecutionHistory] = {}
        
        # 初始化日志记录器
        self.logger = TaskLogger()
        
        # 加载任务（这里可以从数据库或文件加载）
        self._load_tasks()
        
        # 线程锁，用于保护共享资源
        self.lock = threading.RLock()
    
    def _load_tasks(self) -> None:
        """加载任务（这里是示例实现，实际应从数据库加载）"""
        # 这里只是模拟加载，实际应用中应该从数据库或文件系统加载任务
        logger.info("加载任务中...")
        
        # 模拟从数据库加载的任务
        # 在实际应用中，这里应该从数据库或文件系统读取任务数据
    
    def _save_tasks(self) -> None:
        """保存任务（这里是示例实现，实际应保存到数据库）"""
        # 这里只是模拟保存，实际应用中应该将任务保存到数据库或文件系统
        logger.info("保存任务中...")
    
    def create_task(self, task_data: Dict) -> TaskModel:
        """创建新任务
        
        参数:
            task_data: 任务数据字典
        
        返回:
            TaskModel: 创建的任务对象
        
        异常:
            ValueError: 任务数据无效时抛出
        """
        # 验证任务数据
        required_fields = ["name", "project_id", "python_env", "command", "schedule_type", "schedule_config"]
        for field in required_fields:
            if field not in task_data:
                raise ValueError(f"缺少必填字段: {field}")
        
        # 生成任务ID
        task_id = str(int(time.time() * 1000))  # 使用时间戳作为任务ID
        
        # 创建任务模型
        task = TaskModel(
            task_id=task_id,
            name=task_data["name"],
            project_id=task_data["project_id"],
            python_env=task_data["python_env"],
            command=task_data["command"],
            schedule_type=task_data["schedule_type"],
            schedule_config=task_data["schedule_config"],
            description=task_data.get("description", ""),
            max_instances=task_data.get("max_instances", 1),
            tags=task_data.get("tags", []),
            status=task_data.get("status", "active")
        )
        
        # 添加到调度器
        self._add_task_to_scheduler(task)
        
        # 保存到内存
        with self.lock:
            self.tasks[task_id] = task
            self.execution_history[task_id] = []
        
        # 保存到数据库
        self._save_tasks()
        
        logger.info(f"创建任务成功: {task.name} (ID: {task_id})")
        return task
    
    def _add_task_to_scheduler(self, task: TaskModel) -> None:
        """将任务添加到调度器
        
        参数:
            task: 任务对象
        """
        # 根据调度类型创建触发器
        trigger = None
        
        if task.schedule_type == "immediate":
            # 立即执行任务（一次性）
            trigger = DateTrigger(run_date=datetime.datetime.now())
        elif task.schedule_type == "interval":
            # 间隔执行
            interval_value = task.schedule_config.get("value", 1)
            interval_unit = task.schedule_config.get("unit", "minutes")
            
            # 构建间隔参数
            interval_kwargs = {interval_unit: interval_value}
            trigger = IntervalTrigger(**interval_kwargs)
        elif task.schedule_type == "one-time":
            # 一次性执行
            run_date_str = task.schedule_config.get("date")
            if run_date_str:
                run_date = datetime.datetime.fromisoformat(run_date_str)
                trigger = DateTrigger(run_date=run_date)
        elif task.schedule_type == "cron":
            # Cron表达式执行
            cron_expr = task.schedule_config.get("expression")
            if cron_expr:
                # 解析Cron表达式（格式：分 时 日 月 周）
                parts = cron_expr.split()
                if len(parts) >= 5:
                    trigger = CronTrigger(
                        minute=parts[0],
                        hour=parts[1],
                        day=parts[2],
                        month=parts[3],
                        day_of_week=parts[4]
                    )
        
        # 添加任务到调度器
        if trigger:
            self.scheduler.add_job(
                func=self._execute_task,
                trigger=trigger,
                id=task.job_id,
                args=[task.task_id],
                name=task.name,
                max_instances=task.max_instances,
                replace_existing=True,
                misfire_grace_time=60  # 允许的最大延迟时间（秒）
            )
            
            # 如果任务状态为暂停，暂停任务
            if task.status == "paused":
                self.scheduler.pause_job(task.job_id)
    
    def get_task(self, task_id: str) -> Optional[TaskModel]:
        """获取任务详情
        
        参数:
            task_id: 任务ID
        
        返回:
            TaskModel: 任务对象，如果不存在返回None
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self, filters: Optional[Dict] = None) -> List[TaskModel]:
        """获取所有任务
        
        参数:
            filters: 过滤条件
        
        返回:
            List[TaskModel]: 任务列表
        """
        with self.lock:
            tasks = list(self.tasks.values())
            
            # 应用过滤条件
            if filters:
                if "status" in filters and filters["status"] != "all":
                    tasks = [t for t in tasks if t.status == filters["status"]]
                if "project_id" in filters and filters["project_id"] != "all":
                    tasks = [t for t in tasks if t.project_id == filters["project_id"]]
                if "name" in filters:
                    tasks = [t for t in tasks if filters["name"] in t.name]
            
            return tasks
    
    def update_task(self, task_id: str, task_data: Dict) -> Optional[TaskModel]:
        """更新任务
        
        参数:
            task_id: 任务ID
            task_data: 新的任务数据
        
        返回:
            TaskModel: 更新后的任务对象，如果任务不存在返回None
        """
        with self.lock:
            if task_id not in self.tasks:
                return None
            
            task = self.tasks[task_id]
            
            # 更新任务属性
            if "name" in task_data:
                task.name = task_data["name"]
            if "project_id" in task_data:
                task.project_id = task_data["project_id"]
            if "python_env" in task_data:
                task.python_env = task_data["python_env"]
            if "command" in task_data:
                task.command = task_data["command"]
            if "description" in task_data:
                task.description = task_data["description"]
            if "max_instances" in task_data:
                task.max_instances = task_data["max_instances"]
            if "tags" in task_data:
                task.tags = task_data["tags"]
            
            # 如果更新了调度信息，需要重新添加到调度器
            update_schedule = False
            if "schedule_type" in task_data:
                task.schedule_type = task_data["schedule_type"]
                update_schedule = True
            if "schedule_config" in task_data:
                task.schedule_config = task_data["schedule_config"]
                update_schedule = True
            
            # 更新状态
            if "status" in task_data:
                task.status = task_data["status"]
                
                # 如果状态变为活跃或暂停，需要更新调度器中的任务状态
                if task.status == "active":
                    if task.job_id in self.scheduler.get_jobs():
                        self.scheduler.resume_job(task.job_id)
                elif task.status == "paused":
                    if task.job_id in self.scheduler.get_jobs():
                        self.scheduler.pause_job(task.job_id)
            
            # 更新时间
            task.updated_at = datetime.datetime.now()
            
            # 如果调度信息有更新，重新添加到调度器
            if update_schedule:
                # 先移除旧任务
                if task.job_id in self.scheduler.get_jobs():
                    self.scheduler.remove_job(task.job_id)
                # 再添加新任务
                self._add_task_to_scheduler(task)
            
            # 保存到数据库
            self._save_tasks()
            
            logger.info(f"更新任务成功: {task.name} (ID: {task_id})")
            return task
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务
        
        参数:
            task_id: 任务ID
        
        返回:
            bool: 删除成功返回True，失败返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 从调度器中移除任务
            if task.job_id in self.scheduler.get_jobs():
                self.scheduler.remove_job(task.job_id)
            
            # 从内存中移除任务
            del self.tasks[task_id]
            if task_id in self.execution_history:
                del self.execution_history[task_id]
            
            # 保存到数据库
            self._save_tasks()
            
            logger.info(f"删除任务成功: {task.name} (ID: {task_id})")
            return True
    
    def pause_task(self, task_id: str) -> bool:
        """暂停任务
        
        参数:
            task_id: 任务ID
        
        返回:
            bool: 暂停成功返回True，失败返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 更新任务状态
            task.status = "paused"
            task.updated_at = datetime.datetime.now()
            
            # 暂停调度器中的任务
            if task.job_id in self.scheduler.get_jobs():
                self.scheduler.pause_job(task.job_id)
            
            # 保存到数据库
            self._save_tasks()
            
            logger.info(f"暂停任务成功: {task.name} (ID: {task_id})")
            return True
    
    def resume_task(self, task_id: str) -> bool:
        """恢复任务
        
        参数:
            task_id: 任务ID
        
        返回:
            bool: 恢复成功返回True，失败返回False
        """
        with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # 更新任务状态
            task.status = "active"
            task.updated_at = datetime.datetime.now()
            
            # 恢复调度器中的任务
            if task.job_id in self.scheduler.get_jobs():
                self.scheduler.resume_job(task.job_id)
            
            # 保存到数据库
            self._save_tasks()
            
            logger.info(f"恢复任务成功: {task.name} (ID: {task_id})")
            return True
    
    def run_task_now(self, task_id: str) -> str:
        """立即运行任务
        
        参数:
            task_id: 任务ID
        
        返回:
            str: 执行实例ID
        
        异常:
            ValueError: 任务不存在时抛出
        """
        with self.lock:
            if task_id not in self.tasks:
                raise ValueError(f"任务不存在: {task_id}")
            
            task = self.tasks[task_id]
            
            # 生成执行实例ID
            execution_id = f"{task_id}_{int(time.time() * 1000)}"
            
            # 记录执行历史
            execution = ExecutionHistory(
                execution_id=execution_id,
                task_id=task_id,
                start_time=datetime.datetime.now()
            )
            
            # 将执行实例添加到当前执行列表
            self.current_executions[execution_id] = execution
            
            # 如果执行历史列表不存在，创建它
            if task_id not in self.execution_history:
                self.execution_history[task_id] = []
            
            # 添加到执行历史
            self.execution_history[task_id].append(execution)
            
            # 在新线程中执行任务
            threading.Thread(target=self._execute_task, args=[task_id, execution_id]).start()
            
            logger.info(f"立即执行任务: {task.name} (ID: {task_id}, Execution ID: {execution_id})")
            return execution_id
    
    def _execute_task(self, task_id: str, execution_id: Optional[str] = None) -> None:
        """执行任务的内部方法
        
        参数:
            task_id: 任务ID
            execution_id: 执行实例ID（如果为None则自动生成）
        """
        # 获取任务
        task = self.get_task(task_id)
        if not task:
            logger.error(f"执行任务失败：任务不存在: {task_id}")
            return
        
        # 如果没有提供执行实例ID，生成一个
        if not execution_id:
            execution_id = f"{task_id}_{int(time.time() * 1000)}"
        
        # 记录开始执行日志
        self.logger.write_log(execution_id, f"任务开始执行: {task.name}")
        
        # 记录执行开始时间
        start_time = datetime.datetime.now()
        
        try:
            # 执行命令
            self.logger.write_log(execution_id, f"开始执行命令: {task.command}")
            
            # 这里是执行命令的逻辑，实际应用中应该使用subprocess模块执行命令
            # 为了演示，这里只是模拟执行
            time.sleep(2)  # 模拟执行时间
            
            # 记录执行结果
            self.logger.write_log(execution_id, f"命令执行成功")
            status = "success"
            error_message = None
            
        except Exception as e:
            # 记录执行错误
            error_message = str(e)
            self.logger.write_log(execution_id, f"执行失败: {error_message}", "ERROR")
            status = "failed"
            
        finally:
            # 记录结束时间和执行时长
            end_time = datetime.datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # 更新执行历史
            with self.lock:
                if execution_id in self.current_executions:
                    execution = self.current_executions[execution_id]
                    execution.end_time = end_time
                    execution.status = status
                    execution.duration = duration
                    execution.error_message = error_message
                    
                    # 从当前执行列表中移除
                    del self.current_executions[execution_id]
            
            # 记录执行完成日志
            self.logger.write_log(execution_id, f"任务执行完成，耗时: {duration:.2f} 秒")
            
            logger.info(f"任务执行完成: {task.name} (ID: {task_id}, Execution ID: {execution_id}, Status: {status})")
    
    def get_execution_history(self, task_id: str, filters: Optional[Dict] = None) -> List[ExecutionHistory]:
        """获取任务执行历史
        
        参数:
            task_id: 任务ID
            filters: 过滤条件
        
        返回:
            List[ExecutionHistory]: 执行历史列表
        """
        with self.lock:
            if task_id not in self.execution_history:
                return []
            
            history = self.execution_history[task_id]
            
            # 应用过滤条件
            if filters:
                if "status" in filters and filters["status"] != "all":
                    history = [h for h in history if h.status == filters["status"]]
                if "start_time" in filters:
                    start_time = datetime.datetime.fromisoformat(filters["start_time"])
                    history = [h for h in history if h.start_time >= start_time]
                if "end_time" in filters:
                    end_time = datetime.datetime.fromisoformat(filters["end_time"])
                    history = [h for h in history if h.start_time <= end_time]
            
            # 按开始时间降序排序
            history.sort(key=lambda x: x.start_time, reverse=True)
            
            return history
    
    def get_task_logs(self, execution_id: str, filters: Optional[Dict] = None) -> List[str]:
        """获取任务执行日志
        
        参数:
            execution_id: 执行实例ID
            filters: 过滤条件
        
        返回:
            List[str]: 日志条目列表
        """
        # 解析过滤条件
        start_time = None
        end_time = None
        level = None
        keyword = None
        
        if filters:
            if "start_time" in filters:
                start_time = datetime.datetime.fromisoformat(filters["start_time"])
            if "end_time" in filters:
                end_time = datetime.datetime.fromisoformat(filters["end_time"])
            if "level" in filters and filters["level"] != "all":
                level = filters["level"]
            if "keyword" in filters:
                keyword = filters["keyword"]
        
        # 读取日志
        return self.logger.read_logs(execution_id, start_time, end_time, level, keyword)
    
    def download_task_logs(self, execution_id: str) -> str:
        """下载任务执行日志
        
        参数:
            execution_id: 执行实例ID
        
        返回:
            str: 日志文件路径
        """
        return self.logger.download_logs(execution_id)
    
    def stop_execution(self, execution_id: str) -> bool:
        """停止正在执行的任务实例
        
        参数:
            execution_id: 执行实例ID
        
        返回:
            bool: 停止成功返回True，失败返回False
        """
        # 这里只是示例实现，实际应用中应该终止对应的进程
        with self.lock:
            if execution_id not in self.current_executions:
                return False
            
            # 记录停止日志
            self.logger.write_log(execution_id, "任务实例被强制停止", "WARNING")
            
            # 更新执行历史
            execution = self.current_executions[execution_id]
            execution.end_time = datetime.datetime.now()
            execution.status = "failed"
            execution.error_message = "任务被强制停止"
            execution.duration = (execution.end_time - execution.start_time).total_seconds()
            
            # 从当前执行列表中移除
            del self.current_executions[execution_id]
            
            logger.info(f"任务实例被停止: {execution_id}")
            return True
    
    def shutdown(self) -> None:
        """关闭任务管理器和调度器"""
        # 关闭调度器
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("调度器已关闭")
        
        # 保存任务
        self._save_tasks()
        logger.info("任务管理器已关闭")


# 创建任务管理器单例
_task_manager_instance = None


def get_task_manager() -> TaskManager:
    """获取任务管理器单例
    
    返回:
        TaskManager: 任务管理器实例
    """
    global _task_manager_instance
    if _task_manager_instance is None:
        _task_manager_instance = TaskManager()
    return _task_manager_instance


# 示例使用
if __name__ == "__main__":
    try:
        # 创建任务管理器
        task_manager = get_task_manager()
        
        # 创建一个间隔执行的任务示例
        task_data = {
            "name": "示例任务",
            "project_id": "1",
            "python_env": "my_env",
            "command": "python test.py",
            "schedule_type": "interval",
            "schedule_config": {
                "value": 5,
                "unit": "minutes"
            },
            "description": "这是一个示例任务",
            "max_instances": 1,
            "tags": ["测试", "示例"]
        }
        
        # 创建任务
        task = task_manager.create_task(task_data)
        print(f"创建任务成功: {task.name} (ID: {task.task_id})")
        
        # 立即运行任务
        execution_id = task_manager.run_task_now(task.task_id)
        print(f"立即运行任务，执行ID: {execution_id}")
        
        # 等待一段时间，让任务执行完成
        time.sleep(3)
        
        # 获取执行历史
        history = task_manager.get_execution_history(task.task_id)
        print(f"任务执行历史数量: {len(history)}")
        
        # 获取日志
        logs = task_manager.get_task_logs(execution_id)
        print(f"日志数量: {len(logs)}")
        
        # 暂停任务
        task_manager.pause_task(task.task_id)
        print(f"任务已暂停")
        
        # 恢复任务
        task_manager.resume_task(task.task_id)
        print(f"任务已恢复")
        
        # 删除任务
        # task_manager.delete_task(task.task_id)
        # print(f"任务已删除")
        
        # 保持程序运行一段时间
        print("任务管理器正在运行，按Ctrl+C退出...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("程序被用户中断")
    finally:
        # 关闭任务管理器
        if 'task_manager' in locals():
            task_manager.shutdown()