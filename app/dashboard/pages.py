"""NiceGUI前端页面定义

包含所有UI页面的定义和组件
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime

from nicegui import app, ui, Client
import httpx

from app.config.config_manager import config_manager

logger = logging.getLogger('python_envs')

# API基础URL - 从配置管理器获取
API_BASE_URL = config_manager.get_api_base_url()


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
                ui.button('任务管理', on_click=lambda: ui.navigate.to('/tasks'))
                ui.button('虚拟环境', on_click=lambda: ui.navigate.to('/environments'))
                ui.button('项目管理', on_click=lambda: ui.navigate.to('/projects'))
                ui.dark_mode().bind_value(app.storage.user, 'dark_mode')
                    # ui.checkbox('深色模式').bind_value(app.storage.user, 'dark_mode')
    
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
                ).classes('w-full')
        
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
                # ui.input(placeholder='搜索环境...') # .bind_value_to(ui.query('#env-table'), 'options.q')
            
            # 环境列表
            env_table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True},
                    {'name': 'name', 'label': '名称', 'field': 'name', 'required': True},
                    {'name': 'python_version', 'label': 'Python版本', 'field': 'python_version', 'required': True},
                    {'name': 'status', 'label': '状态', 'field': 'status', 'required': True},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'required': True},
                ],
                rows=[]
            ).classes('w-full')

            
        
        # # 创建环境对话框
        # def open_create_env_dialog():
        #     with ui.dialog() as dialog, ui.card():
        #         ui.label('创建新虚拟环境').classes('text-xl font-bold mb-4')
        #         with ui.column().classes('gap-4'):
        #             name_input = ui.input(label='环境名称')
        #             version_input = ui.input(label='Python版本')
        #             with ui.row().classes('justify-end gap-2'):
        #                 ui.button('取消', on_click=dialog.close)
        #                 ui.button('创建', on_click=lambda: create_env(name_input.value, version_input.value, dialog))
        
        # async def create_env(name: str, version: str, dialog):
        #     if not name or not version:
        #         ui.notify('请填写所有字段', type='negative')
        #         return
        #     # 这里应该调用API创建环境
        #     ui.notify(f'创建环境: {name}', type='positive')
        #     dialog.close()
        #     # 刷新列表
        #     await load_envs()
        
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
        
        # async def show_env_details(env):
        #     with ui.dialog() as dialog, ui.card():
        #         ui.label(f'环境详情: {env["name"]}').classes('text-xl font-bold mb-4')
        #         # 显示环境详情
        #         dialog.open()
        
        # async def delete_env(env_id):
        #     # 这里应该调用API删除环境
        #     ui.notify(f'删除环境: {env_id}', type='negative')
        #     await load_envs()
        
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
        # 操作按钮
        with ui.row().classes('w-full'):
            ui.button('创建新任务', on_click=lambda: open_create_task_dialog())
            
        # 主内容区
        with ui.column().classes('w-full items-center gap-6 p-6'):
            # 任务列表
            tasks_table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True},
                    {'name': 'name', 'label': '任务名称', 'field': 'name', 'required': True},
                    {'name': 'description', 'label': '描述', 'field': 'description', 'required': False},
                    {'name': 'python_env', 'label': 'Python环境', 'field': 'python_env', 'required': False},
                    {'name': 'schedule_type', 'label': '调度类型', 'field': 'schedule_type', 'required': False},
                    {'name': 'status', 'label': '状态', 'field': 'status', 'required': True},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'required': True},
                ],
                rows=[]
            ).classes('w-full')
        
        # 加载任务列表
        async def load_tasks():
            try:
                # 调用API接口获取任务数据
                data = await DashboardUI.fetch_api_data('/tasks')
                
                # 处理API响应
                tasks = []
                if isinstance(data, dict):
                    # API返回包含data字段的对象
                    if 'data' in data and isinstance(data['data'], list):
                        # 从data字段中提取任务列表
                        for task in data['data']:
                            # 转换为字典格式，确保可序列化
                            task_dict = {
                                'id': task.id,
                                'name': task.name,
                                'status': 'running' if task.is_active else 'idle',
                                'description': task.description or '',
                                'python_env': task.python_env.name if task.python_env else '',
                                'schedule_type': task.schedule_type,
                                'next_run_time': getattr(task, 'next_run_time', ''),
                                'actions': ''
                            }
                            tasks.append(task_dict)
                elif isinstance(data, list):
                    # API直接返回任务列表
                    for task in data:
                        task_dict = {
                            'id': task.id if hasattr(task, 'id') else task.get('id'),
                            'name': task.name if hasattr(task, 'name') else task.get('name', ''),
                            'status': 'running' if (hasattr(task, 'is_active') and task.is_active) else 'idle',
                            'description': task.description if hasattr(task, 'description') else task.get('description', ''),
                            'actions': ''
                        }
                        tasks.append(task_dict)
                
                # 为每行添加操作按钮
                for task in tasks:
                    with ui.row() as buttons:
                        if task['status'] == 'running':
                            ui.button('暂停', on_click=lambda t=task: pause_task(t['id']))
                        else:
                            ui.button('启动', on_click=lambda t=task: start_task(t['id']))
                        ui.button('查看日志', on_click=lambda t=task: view_task_logs(t['id']))
                    task['actions'] = buttons
                
                # 更新表格数据
                tasks_table.rows = tasks
                
                if not tasks:
                    ui.notify('暂无任务数据', type='info')
                    
            except Exception as e:
                ui.notify(f'加载任务失败: {str(e)}', type='negative')
                logger.error(f'加载任务失败: {str(e)}')
                # 使用模拟数据作为降级方案
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
        with ui.row().classes('w-full'):
            ui.button('新建项目', on_click=lambda: open_create_project_dialog())
        # 主内容区
        with ui.column().classes('w-full items-center gap-6 p-6'):
            # 项目列表
            projects_table = ui.table(
                columns=[
                    {'name': 'id', 'label': 'ID', 'field': 'id', 'required': True},
                    {'name': 'name', 'label': '项目名称', 'field': 'name', 'required': True},
                    {'name': 'work_path', 'label': '工作目录', 'field': 'work_path', 'required': True},
                    {'name': 'description', 'label': '描述', 'field': 'description', 'required': True},
                    {'name': 'tags', 'label': '标签', 'field': 'tags', 'required': True},
                    {'name': 'tasks_count', 'label': '任务数量', 'field': 'tasks_count', 'required': True},
                    {'name': 'actions', 'label': '操作', 'field': 'actions', 'required': True},
                ],
                rows=[]
            ).classes('w-full')
            projects_table.add_slot('body-cell-actions', '''
            <q-td key="actions" :props="props">
                <q-btn flat dense round icon="edit" color="primary"
                    @click="$parent.$emit('edit', props.row)" />
                <q-btn flat dense round icon="delete" color="negative"
                    @click="$parent.$emit('delete', props.row)" />
            </q-td>
            ''')

            projects_table.on('edit', lambda e: show_project_edit_dialog(e.args))
            projects_table.on('delete', lambda e: show_project_delete_dialog(e.args))

        async def show_project_edit_dialog(project):
            print(project)
            with ui.dialog() as dialog, ui.card():
                ui.label('编辑项目').classes('text-xl font-bold mb-4')
                with ui.column().classes('space-y-2'):
                    ui.input('项目名称', value=project['name']).bind_value(project, 'name')
                    ui.input('描述', value=project['description']).bind_value(project, 'description')
                with ui.row().classes('justify-end'):
                    ui.button('取消', on_click=dialog.close)
                    ui.button('保存', on_click=lambda: save_project_changes(project, dialog))
                dialog.open()

        async def save_project_changes(project, dialog: ui.dialog):
            try:
                # 准备API请求数据
                project_data = {
                    "name": project["name"],
                    "description": project["description"],
                    "work_path": project["work_path"],
                    "source_type": project["source_type"],
                    "source_url": project["git_url"] if project["source_type"] == "git" else None,
                    "branch": project["git_branch"] if project["source_type"] == "git" else None,
                    "git_username": project["git_username"] if project["source_type"] == "git" else None,
                    "git_password": project["git_password"] if project["source_type"] == "git" else None,
                    "tags": project.get("tags", [])  # 直接使用标签列表
                }
                
                # 直接使用httpx.AsyncClient发送POST请求
                async with httpx.AsyncClient() as client:
                    response = await client.post(f"{API_BASE_URL}/projects", json=project_data)
                    response.raise_for_status()
                    result = response.json()
                
                # 成功创建项目
                ui.notify(f'成功创建项目: {project["name"]}', type='positive', position='top')
                await load_projects()
                dialog.close()
                
            except httpx.HTTPStatusError as e:
                # 从响应中获取错误信息
                error_detail = ""
                try:
                    error_data = e.response.json()
                    if isinstance(error_data, dict):
                        if "detail" in error_data:
                            error_detail = error_data["detail"]
                        elif "error" in error_data:
                            error_detail = error_data["error"]
                except:
                    pass
                
                if e.response.status_code == 400:
                    if error_detail:
                        ui.notify(f'创建项目失败: {error_detail}', type='negative', position='top')
                    elif "项目名称已存在" in str(e):
                        ui.notify('创建项目失败: 项目名称已存在', type='negative', position='top')
                    else:
                        ui.notify('创建项目失败: 参数错误，请检查输入', type='negative', position='top')
                elif e.response.status_code == 500:
                    ui.notify('创建项目失败: 服务器内部错误', type='negative', position='top')
                else:
                    ui.notify(f'创建项目失败: HTTP错误 {e.response.status_code}', type='negative', position='top')
                logger.error(f'HTTP错误: {str(e)}')
            except Exception as e:
                ui.notify(f'创建项目失败: {str(e)}', type='negative', position='top')
                logger.error(f'创建项目失败: {str(e)}')

        async def open_create_project_dialog():
            # 初始化项目数据
            project = {
                'name': '',
                'work_path': '/',
                'description': '',
                'tags': [],
                'source_type': 'git',  # 默认Git仓库
                'git_url': 'https://github.com/username/repository.git',
                'git_branch': 'main',
                'git_username': '',
                'git_password': '',
                'uploaded_file': None
            }
            
            # 使用可绑定的引用来存储组件
            class Ref:
                def __init__(self):
                    self.value = None
            
            tag_input_ref = Ref()
            tags_container_ref = Ref()
            source_area_ref = Ref()
            
            # 标签处理已经通过input_chips组件直接处理
            
            # 标签删除已经通过input_chips组件直接处理

            # 标签显示已经通过input_chips组件直接处理
            # 表单验证函数
            def validate_form():
                # 检查必填项
                if not project['name'].strip():
                    ui.notify('请输入项目名称', type='negative')
                    return False
                if not project['work_path'].strip():
                    ui.notify('请输入工作路径', type='negative')
                    return False
                # 根据项目来源检查相应字段
                if project['source_type'] == 'zip' and not project['uploaded_file']:
                    ui.notify('请上传ZIP文件', type='negative')
                    return False
                elif project['source_type'] == 'git' and not project['git_url'].strip():
                    ui.notify('请输入Git仓库URL', type='negative')
                    return False
                # 检查工作路径是否包含中文字符
                if any('\u4e00' <= c <= '\u9fff' for c in project['work_path']):
                    ui.notify('工作路径不能包含中文字符', type='negative')
                    return False
                return True
            
            # 根据项目来源更新输入区域
            def update_source_area():
                if source_area_ref.value:
                    with source_area_ref.value:
                        source_area_ref.value.clear()
                        if project['source_type'] == 'zip':
                            # ZIP上传区域
                            with ui.card().classes('border-dashed border-2 border-gray-300 p-8 text-center rounded-lg'):
                                ui.icon('upload').classes('text-4xl text-gray-400 mb-2')
                                ui.label('拖拽ZIP文件到此，或点击选择').classes('mb-2')
                                upload = ui.upload(on_upload=lambda e: handle_file_upload(e, project))
                                upload.props('accept=".zip" label="点击上传"')
                                if project['uploaded_file']:
                                    ui.label(f'已选择文件: {project["uploaded_file"]}').classes('text-green-600 mt-2')
                        else:
                            # Git仓库输入区域
                            with ui.column().classes('space-y-3'):
                                with ui.column().classes('space-y-1'):
                                    ui.label('Git仓库地址 *').classes('text-sm font-medium')
                                    ui.input().classes('w-full').bind_value(project, 'git_url')
                                with ui.column().classes('space-y-1'):
                                    ui.label('分支').classes('text-sm font-medium')
                                    ui.input().classes('w-full').bind_value(project, 'git_branch')
                                with ui.column().classes('space-y-1'):
                                    ui.label('用户名').classes('text-sm font-medium')
                                    ui.input().classes('w-full').props('placeholder="Git用户名 (可选)"').bind_value(project, 'git_username')
                                with ui.column().classes('space-y-1'):
                                    ui.label('密码').classes('text-sm font-medium')
                                    ui.input(password=True).classes('w-full').props('placeholder="Git密码 (可选)"').bind_value(project, 'git_password')
                                ui.label('请输入Git仓库的访问凭证').classes('text-xs text-gray-500 mt-1')
            
            # 处理文件上传
            def handle_file_upload(event, project):
                if event.name:
                    project['uploaded_file'] = event.name
                    update_source_area()
            
            # 创建对话框
            with ui.dialog() as dialog, ui.card().classes('w-full max-h-[80vh]'):

                # 标题
                ui.label('新项目').classes('text-xl font-bold mb-4')
                
                # 添加滚动容器，包裹所有表单内容
                with ui.scroll_area().classes('h-[calc(80vh-120px)] w-full'):
                    # 表单容器
                    # 项目名称
                    ui.label('项目名称 *').classes('text-sm font-medium')
                    ui.input().classes('w-full').props('placeholder="请输入项目名称"').bind_value(project, 'name')
                    
                    # 工作路径
                    ui.label('工作路径 *').classes('text-sm font-medium')
                    ui.input(value='/').classes('w-full').props('placeholder="/project_name"').bind_value(project, 'work_path')
                    ui.label('工作路径建议为默认/,即不需要修改').classes('text-xs text-gray-500')
                    
                    # 描述
                    ui.label('描述').classes('text-sm font-medium')
                    ui.textarea().classes('w-full').props('placeholder="请输入项目描述"').bind_value(project, 'description')
                    
                    # 标签
                    ui.input_chips('标签', value=[]).bind_value(project, 'tags')

                    # 项目来源选择
                    with ui.tabs().classes('w-full flex justify-between') as tabs:
                        git_tab = ui.tab('git', label='Git仓库', icon='fork_left').classes('w-1/2 text-center')
                        zip_tab = ui.tab('zip', label='ZIP上传', icon='folder_zip').classes('w-1/2 text-center')
                    with ui.tab_panels(tabs, value=git_tab).classes('w-full'):
                        with ui.tab_panel(zip_tab):
                            print('zip_tab')
                            # ZIP上传区域
                            with ui.card().classes('border-dashed border-2 border-gray-300 p-8 text-center rounded-lg'):
                                ui.icon('upload').classes('text-4xl text-gray-400 mb-2')
                                ui.label('拖拽ZIP文件到此，或点击选择').classes('mb-2')
                                upload = ui.upload(on_upload=lambda e: handle_file_upload(e, project))
                                upload.props('accept=".zip" label="点击上传"')
                                if project['uploaded_file']:
                                    ui.label(f'已选择文件: {project["uploaded_file"]}').classes('text-green-600 mt-2')
                        with ui.tab_panel(git_tab):
                            print('git_tab')
                            ui.label('Git仓库地址 *').classes('text-sm font-medium')
                            ui.input().classes('w-full').bind_value(project, 'git_url')

                            ui.label('分支').classes('text-sm font-medium')
                            ui.input().classes('w-full').bind_value(project, 'git_branch')

                            ui.label('用户名').classes('text-sm font-medium')
                            ui.input().classes('w-full').props('placeholder="Git用户名 (可选)"').bind_value(project, 'git_username')

                            ui.label('密码').classes('text-sm font-medium')
                            ui.input(password=True).classes('w-full').props('placeholder="Git密码 (可选)"').bind_value(project, 'git_password')
                            ui.label('请输入Git仓库的访问凭证').classes('text-xs text-gray-500 mt-1')
                
                # 操作按钮放在滚动容器外
                with ui.row().classes('justify-end right-4 bottom-4'):
                    ui.button('取消', on_click=dialog.close)
                    ui.button('保存', on_click=lambda: save_project_changes(project, dialog) if validate_form() else None, color='primary')
            
                # 初始化显示
                # update_source_area()
            dialog.open()

        # async def project_delete_dialog(project, dialog):
        #     # 这里应该调用API保存项目更改
        #     ui.notify(f'保存项目: {project["name"]}', type='positive')
        #     await load_projects()
        #     dialog.close()
        
        # 加载项目列表
        async def load_projects():
            # 调用API接口获取真实项目数据
            data = await DashboardUI.fetch_api_data('/projects')
            
            # 处理API响应
            projects = []
            if isinstance(data, list):
                # 如果API直接返回项目列表
                projects = data
            elif isinstance(data, dict) and 'data' in data:
                # 如果API返回包含data字段的对象
                if isinstance(data['data'], list):
                    projects = data['data']
                elif 'projects' in data['data']:
                    projects = data['data']['projects']
            
            # 为每行添加操作按钮并准备表格数据
            table_data = []
            for project in projects:
                # 准备表格行数据，正确处理标签数据
                tags = project.get('tags', [])
                # 将标签列表转换为逗号分隔的字符串
                tags_str = ''
                if isinstance(tags, list):
                    if tags and isinstance(tags[0], dict):
                        # 如果标签是对象列表
                        tags_str = ', '.join([tag.get('name', '') for tag in tags])
                    else:
                        # 如果标签是字符串列表
                        tags_str = ', '.join(tags)
                
                row_data = {
                    'id': project.get('id', ''),
                    'name': project.get('name', ''),
                    'description': project.get('description', ''),
                    'work_path': project.get('work_path', ''),
                    'tags': tags_str,  # 使用处理后的标签字符串
                    'tasks_count': project.get('tasks_count', ''),
                }
                table_data.append(row_data)
            
            # 更新表格数据
            projects_table.rows = table_data
            if not table_data:
                ui.notify('暂无项目数据', type='info')
        
        async def show_project_details(project):
            with ui.dialog() as dialog, ui.card():
                # 安全获取项目名称
                project_name = project.get('name', '未知项目')
                ui.label(f'项目详情: {project_name}').classes('text-xl font-bold mb-4')
                
                # 显示项目详细信息
                with ui.column().classes('space-y-2'):
                    ui.label(f'ID: {project.get("id", "")}')
                    ui.label(f'描述: {project.get("description", "无描述")}')
                    ui.label(f'状态: {project.get("status", "")}')
                    ui.label(f'创建时间: {project.get("create_time", "")}')
                    
                    # 如果有标签信息，显示标签
                    tags_info = ''
                    if 'tags' in project:
                        if isinstance(project['tags'], list):
                            if project['tags'] and isinstance(project['tags'][0], dict):
                                # 标签是对象列表
                                tags_info = ', '.join([tag.get('name', '') for tag in project['tags']])
                            else:
                                # 标签是字符串列表
                                tags_info = ', '.join(project['tags'])
                    if tags_info:
                        ui.label(f'标签: {tags_info}')
                
                dialog.open()
        
        ui.timer(0.1, load_projects, once=True)
        
        async def show_project_delete_dialog(project):
            """显示项目删除确认对话框
            
            Args:
                project: 要删除的项目对象
            """
            with ui.dialog() as dialog, ui.card():
                # 对话框标题和提示信息
                ui.label('删除项目确认').classes('text-xl font-bold mb-4')
                ui.label(f'确定要删除项目「{project.get("name", "")}」吗？').classes('mb-4')
                ui.label('此操作不可撤销，删除后数据将无法恢复。').classes('text-red-500 mb-6')
                
                # 操作按钮
                with ui.row().classes('justify-end gap-4'):
                    ui.button('取消', on_click=dialog.close)
                    ui.button('删除', on_click=lambda: confirm_delete(project, dialog), color='negative')
                
                dialog.open()
        
        async def confirm_delete(project, dialog: ui.dialog):
            """确认删除项目，调用API执行删除操作
            
            Args:
                project: 要删除的项目对象
                dialog: 对话框实例
            """
            try:
                # 获取项目ID
                project_id = project.get('id')
                if not project_id:
                    ui.notify('无法获取项目ID，删除失败', type='negative')
                    dialog.close()
                    return
                
                # 调用API删除项目
                async with httpx.AsyncClient() as client:
                    response = await client.delete(f"{API_BASE_URL}/projects/{project_id}")
                    response.raise_for_status()
                
                # 删除成功，显示成功消息并重新加载项目列表
                ui.notify(f'成功删除项目: {project.get("name", "")}', type='positive')
                await load_projects()
                dialog.close()
                
            except httpx.HTTPStatusError as e:
                # 处理HTTP错误
                error_detail = ""
                try:
                    error_data = e.response.json()
                    if isinstance(error_data, dict):
                        if "detail" in error_data:
                            error_detail = error_data["detail"]
                        elif "error" in error_data:
                            error_detail = error_data["error"]
                except:
                    pass
                
                if e.response.status_code == 404:
                    ui.notify(f'删除失败: 项目不存在', type='negative')
                elif e.response.status_code == 400:
                    ui.notify(f'删除失败: {error_detail or "参数错误"}', type='negative')
                elif e.response.status_code == 500:
                    ui.notify(f'删除失败: 服务器内部错误', type='negative')
                else:
                    ui.notify(f'删除失败: HTTP错误 {e.response.status_code}', type='negative')
                logger.error(f'删除项目HTTP错误: {str(e)}')
            except Exception as e:
                # 处理其他异常
                ui.notify(f'删除项目失败: {str(e)}', type='negative')
                logger.error(f'删除项目失败: {str(e)}')
        