"""NiceGUI前端页面定义

包含所有UI页面的定义和组件
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from nicegui import app, ui, Client
import httpx

logger = logging.getLogger('python_envs')

# API基础URL
API_BASE_URL = '/api'


# 根路径重定向到仪表板
@ui.page('/')
def redirect_to_dashboard():
    ui.navigate.to('/dashboard')


class DashboardUI:
    """仪表板UI类"""
    
    @staticmethod
    async def fetch_api_data(endpoint: str) -> Dict[str, Any]:
        """获取API数据
        
        Args:
            endpoint: API端点
            
        Returns:
            API响应数据
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{API_BASE_URL}{endpoint}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"获取API数据失败 ({endpoint}): {str(e)}")
            ui.notify(f"获取数据失败: {str(e)}", type='negative')
            return {}
    
    @staticmethod
    @ui.page('/dashboard')
    def dashboard_page(client: Client) -> None:
        """仪表板主页面
        
        Args:
            client: NiceGUI客户端实例
        """
        # 设置页面标题
        ui.query('meta[name="viewport"]').props('content="width=device-width, initial-scale=1.0"')
        
        # 创建顶部导航栏
        with ui.header(elevated=True).classes('items-center justify-between'):
            ui.label('任务管理系统').classes('text-2xl font-bold')
            with ui.row():
                    ui.button('虚拟环境', on_click=lambda: ui.navigate.to('/environments'))
                    ui.button('任务管理', on_click=lambda: ui.navigate.to('/tasks'))
                    ui.button('项目管理', on_click=lambda: ui.navigate.to('/projects'))
                    ui.dark_mode().bind_value(app.storage.user, 'dark_mode')
                    ui.checkbox('深色模式').bind_value(app.storage.user, 'dark_mode')
    
        # 主内容区
        with ui.column().classes('w-full items-center gap-6 p-6'):
            ui.label('系统概览').classes('text-3xl font-bold')
            
            # 统计卡片
            with ui.row().classes('w-full justify-between'):
                with ui.card().classes('w-1/4 p-4'):
                    ui.label('虚拟环境').classes('text-lg')
                    env_count = ui.label('0').classes('text-4xl font-bold')
                
                with ui.card().classes('w-1/4 p-4'):
                    ui.label('活跃任务').classes('text-lg')
                    task_count = ui.label('0').classes('text-4xl font-bold')
                
                with ui.card().classes('w-1/4 p-4'):
                    ui.label('项目数量').classes('text-lg')
                    project_count = ui.label('0').classes('text-4xl font-bold')
                
                with ui.card().classes('w-1/4 p-4'):
                    ui.label('系统状态').classes('text-lg')
                    status = ui.label('正常').classes('text-4xl font-bold text-green-500')
            
            # 最近活动
            with ui.card().classes('w-full p-4'):
                ui.label('最近活动').classes('text-xl font-bold mb-4')
                activity_table = ui.table(
                    columns=[
                        {'name': 'time', 'label': '时间', 'field': 'time', 'required': True},
                        {'name': 'action', 'label': '操作', 'field': 'action', 'required': True},
                        {'name': 'status', 'label': '状态', 'field': 'status', 'required': True},
                    ],
                    rows=[]
                )
        
        # 加载数据
        async def load_data():
            # 这里应该根据实际API获取数据
            # 模拟数据
            env_count.text = '5'
            task_count.text = '3'
            project_count.text = '12'
            
            # 模拟活动数据
            activities = [
                {'time': '2024-01-20 10:30', 'action': '创建虚拟环境', 'status': '成功'},
                {'time': '2024-01-20 09:15', 'action': '运行任务', 'status': '进行中'},
                {'time': '2024-01-20 08:45', 'action': '更新依赖', 'status': '成功'},
            ]
            activity_table.rows = activities
        
        ui.timer(0.1, load_data, once=True)
    
    @staticmethod
    @ui.page('/environments')
    def environments_page(client: Client) -> None:
        """虚拟环境管理页面
        
        Args:
            client: NiceGUI客户端实例
        """
        # 创建顶部导航栏
        with ui.header(elevated=True).classes('items-center justify-between'):
            ui.label('虚拟环境管理').classes('text-2xl font-bold')
            with ui.row():
                    ui.button('返回仪表板', on_click=lambda: ui.navigate.to('/dashboard'))
        
        # 主内容区
        with ui.column().classes('w-full items-center gap-6 p-6'):
            # 操作按钮
            with ui.row().classes('w-full justify-between'):
                ui.button('创建新环境', on_click=lambda: open_create_env_dialog())
                ui.input(placeholder='搜索环境...').bind_value_to(ui.query('#env-table'), 'options.q')
            
            # 环境列表
            env_table = ui.table(
                id='env-table',
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True},
                    {'name': 'name', 'label': '名称', 'field': 'name', 'required': True},
                    {'name': 'python_version', 'label': 'Python版本', 'field': 'python_version', 'required': True},
                    {'name': 'status', 'label': '状态', 'field': 'status', 'required': True},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'required': True},
                ],
                rows=[]
            ).classes('w-full')
        
        # 创建环境对话框
        def open_create_env_dialog():
            with ui.dialog() as dialog, ui.card():
                ui.label('创建新虚拟环境').classes('text-xl font-bold mb-4')
                with ui.column().classes('gap-4'):
                    name_input = ui.input(label='环境名称')
                    version_input = ui.input(label='Python版本')
                    with ui.row().classes('justify-end gap-2'):
                        ui.button('取消', on_click=dialog.close)
                        ui.button('创建', on_click=lambda: create_env(name_input.value, version_input.value, dialog))
        
        async def create_env(name: str, version: str, dialog):
            if not name or not version:
                ui.notify('请填写所有字段', type='negative')
                return
            # 这里应该调用API创建环境
            ui.notify(f'创建环境: {name}', type='positive')
            dialog.close()
            # 刷新列表
            await load_envs()
        
        # 加载环境列表
        async def load_envs():
            # 模拟数据
            envs = [
                {'id': 1, 'name': 'env1', 'python_version': '3.9.10', 'status': 'active', 'actions': '操作按钮'}, 
                {'id': 2, 'name': 'env2', 'python_version': '3.10.4', 'status': 'inactive', 'actions': '操作按钮'}
            ]
            # 为每行添加操作按钮
            for env in envs:
                with ui.row() as buttons:
                    ui.button('详情', on_click=lambda e=env: show_env_details(e))
                    ui.button('删除', on_click=lambda e=env: delete_env(e['id']), color='red')
                env['actions'] = buttons
            env_table.rows = envs
        
        async def show_env_details(env):
            with ui.dialog() as dialog, ui.card():
                ui.label(f'环境详情: {env["name"]}').classes('text-xl font-bold mb-4')
                # 显示环境详情
                dialog.open()
        
        async def delete_env(env_id):
            # 这里应该调用API删除环境
            ui.notify(f'删除环境: {env_id}', type='negative')
            await load_envs()
        
        ui.timer(0.1, load_envs, once=True)
    
    @staticmethod
    @ui.page('/tasks')
    def tasks_page(client: Client) -> None:
        """任务管理页面
        
        Args:
            client: NiceGUI客户端实例
        """
        # 创建顶部导航栏
        with ui.header(elevated=True).classes('items-center justify-between'):
            ui.label('任务管理').classes('text-2xl font-bold')
            with ui.row():
                ui.button('返回仪表板', on_click=lambda: ui.navigate.to('/dashboard'))
        
        # 主内容区
        with ui.column().classes('w-full items-center gap-6 p-6'):
            # 任务列表
            tasks_table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True},
                    {'name': 'name', 'label': '任务名称', 'field': 'name', 'required': True},
                    {'name': 'status', 'label': '状态', 'field': 'status', 'required': True},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'required': True},
                ],
                rows=[]
            ).classes('w-full')
        
        # 加载任务列表
        async def load_tasks():
            # 模拟数据
            tasks = [
                {'id': 1, 'name': '备份数据库', 'status': 'running', 'actions': '操作按钮'},
                {'id': 2, 'name': '清理日志', 'status': 'idle', 'actions': '操作按钮'}
            ]
            # 为每行添加操作按钮
            for task in tasks:
                with ui.row() as buttons:
                    if task['status'] == 'running':
                        ui.button('暂停', on_click=lambda t=task: pause_task(t['id']))
                    else:
                        ui.button('启动', on_click=lambda t=task: start_task(t['id']))
                    ui.button('查看日志', on_click=lambda t=task: view_task_logs(t['id']))
                task['actions'] = buttons
            tasks_table.rows = tasks
        
        async def start_task(task_id):
            # 这里应该调用API启动任务
            ui.notify(f'启动任务: {task_id}', type='positive')
            await load_tasks()
        
        async def pause_task(task_id):
            # 这里应该调用API暂停任务
            ui.notify(f'暂停任务: {task_id}', type='warning')
            await load_tasks()
        
        async def view_task_logs(task_id):
            ui.navigate.to(f'/tasks/{task_id}/logs')
        
        ui.timer(0.1, load_tasks, once=True)
    
    @staticmethod
    @ui.page('/projects')
    def projects_page(client: Client) -> None:
        """项目管理页面
        
        Args:
            client: NiceGUI客户端实例
        """
        # 创建顶部导航栏
        with ui.header(elevated=True).classes('items-center justify-between'):
            ui.label('项目管理').classes('text-2xl font-bold')
            with ui.row():
                ui.button('返回仪表板', on_click=lambda: ui.navigate.to('/dashboard'))
        
        # 主内容区
        with ui.column().classes('w-full items-center gap-6 p-6'):
            # 项目列表
            projects_table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True},
                    {'name': 'name', 'label': '项目名称', 'field': 'name', 'required': True},
                    {'name': 'description', 'label': '描述', 'field': 'description', 'required': True},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'required': True},
                ],
                rows=[]
            ).classes('w-full')
        
        # 加载项目列表
        async def load_projects():
            # 模拟数据
            projects = [
                {'id': 1, 'name': '项目A', 'description': '测试项目A', 'actions': '操作按钮'},
                {'id': 2, 'name': '项目B', 'description': '测试项目B', 'actions': '操作按钮'}
            ]
            # 为每行添加操作按钮
            for project in projects:
                with ui.row() as buttons:
                    ui.button('详情', on_click=lambda p=project: show_project_details(p))
                project['actions'] = buttons
            projects_table.rows = projects
        
        async def show_project_details(project):
            with ui.dialog() as dialog, ui.card():
                ui.label(f'项目详情: {project["name"]}').classes('text-xl font-bold mb-4')
                # 显示项目详情
                dialog.open()
        
        ui.timer(0.1, load_projects, once=True)