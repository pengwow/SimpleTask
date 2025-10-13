import dash
from dash import html, dcc, callback, Input, Output, State, ALL, MATCH
import feffery_antd_components as fac
import json
import requests

# 实例化Dash应用对象
app = dash.Dash(__name__)

# 添加自定义CSS样式
app.config.external_stylesheets = ['https://cdn.jsdelivr.net/npm/antd@5.0.0/dist/reset.css']

# 创建管理系统页面布局
def create_layout():
    """创建管理系统的整体布局
    
    返回:
        html.Div: 包含侧边栏、顶部导航和主内容区的页面布局
    """
    return html.Div(
        id="app-container",
        style={
            "display": "flex",
            "flexDirection": "row",
            "height": "100vh",
            "margin": 0,
            "padding": 0,
            "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
        },
        children=[
            # 侧边栏导航
            html.Div(
                id="sidebar",
                style={
                    "width": "200px",
                    "backgroundColor": "#001529",
                    "color": "white",
                    "display": "flex",
                    "flexDirection": "column",
                    "boxShadow": "2px 0 8px 0 rgba(29, 35, 41, 0.05)"
                },
                children=[
                    # 侧边栏标题
                    html.Div(
                        style={
                            "padding": "20px",
                            "borderBottom": "1px solid #002140",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center"
                        },
                        children=[
                            html.Img(
                                src="https://via.placeholder.com/32x32?text=TP",
                                style={"width": "32px", "height": "32px", "marginRight": "10px"}
                            ),
                            html.H2(
                                "SimpleTask",
                                style={"margin": 0, "color": "white", "fontSize": "18px"}
                            )
                        ]
                    ),
                    
                    # 侧边栏菜单项
                    html.Div(
                        style={"padding": "10px 0"},
                        children=[
                            create_menu_item("仪表盘", "dashboard"),
                            create_menu_item("定时任务", "clock-circle", True),
                            create_menu_item("项目", "project"),
                            create_menu_item("Python环境", "code-square"),
                            create_menu_item("用户管理", "user"),
                            create_menu_item("日志管理", "file-text"),
                            create_menu_item("设置", "setting")
                        ]
                    )
                ]
            ),
            
            # 主内容区域
            html.Div(
                style={
                    "flex": 1,
                    "display": "flex",
                    "flexDirection": "column",
                    "backgroundColor": "#f0f2f5"
                },
                children=[
                    # 顶部导航栏
                    html.Div(
                        id="header",
                        style={
                            "height": "64px",
                            "backgroundColor": "white",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "space-between",
                            "padding": "0 24px",
                            "boxShadow": "0 1px 4px rgba(0, 21, 41, 0.08)"
                        },
                        children=[
                            # 顶部左侧
                            html.Div(
                                style={"display": "flex", "alignItems": "center"},
                                children=[
                                    html.Span("定时任务", id="page-title", style={"fontSize": "16px", "fontWeight": "bold"})
                                ]
                            ),
                            
                            # 顶部右侧
                            html.Div(
                                style={"display": "flex", "alignItems": "center", "gap": "16px"},
                                children=[
                                    # 搜索框
                                    html.Div(
                                        style={"position": "relative"},
                                        children=[
                                            dcc.Input(
                                                placeholder="搜索...",
                                                style={
                                                    "width": "200px",
                                                    "height": "32px",
                                                    "paddingLeft": "32px",
                                                    "border": "1px solid #d9d9d9",
                                                    "borderRadius": "4px",
                                                    "outline": "none"
                                                }
                                            ),
                                            html.Span(
                                                className="anticon anticon-search",
                                                style={
                                                    "position": "absolute",
                                                    "left": "8px",
                                                    "top": "50%",
                                                    "transform": "translateY(-50%)",
                                                    "color": "#999"
                                                }
                                            )
                                        ]
                                    ),
                                    
                                    # 语言切换
                                    html.Span("EN", style={"cursor": "pointer"}),
                                    
                                    # 用户信息
                                    html.Div(
                                        style={"display": "flex", "alignItems": "center", "gap": "8px", "cursor": "pointer"},
                                        children=[
                                            html.Img(
                                                src="https://via.placeholder.com/32x32?text=U",
                                                style={"width": "32px", "height": "32px", "borderRadius": "16px"}
                                            ),
                                            html.Span("管理员")
                                        ]
                                    ),
                                    
                                    # 退出按钮
                                    html.Button(
                                        "退出",
                                        style={
                                            "padding": "4px 12px",
                                            "backgroundColor": "transparent",
                                            "border": "1px solid #d9d9d9",
                                            "borderRadius": "4px",
                                            "cursor": "pointer",
                                            "color": "#666"
                                        }
                                    )
                                ]
                            )
                        ]
                    ),
                    
                    # 内容区域
                    html.Div(
                        id="content",
                        style={
                            "flex": 1,
                            "padding": "24px",
                            "overflowY": "auto"
                        },
                        children=[
                            # 任务列表区域
                            fac.AntdCard(
                                title="任务列表",
                                hoverable=True,
                                extra=[
                                    html.Div(
                                        style={"display": "flex", "alignItems": "center", "gap": "10px"},
                                        children=[
                                            # 搜索框
                                            fac.AntdInput(
                                                id="task-search-input",
                                                placeholder="搜索任务...",
                                                style={"width": "200px"},
                                                prefix=fac.AntdIcon(icon="search")
                                            ),
                                            
                                            # 状态筛选
                                            fac.AntdSelect(
                                                id="task-status-filter",
                                                defaultValue="all",
                                                options=[
                                                    {"label": "全部状态", "value": "all"},
                                                    {"label": "活跃中", "value": "active"},
                                                    {"label": "已暂停", "value": "paused"},
                                                    {"label": "错误", "value": "error"}
                                                ],
                                                style={"width": "120px"}
                                            ),
                                            
                                            # 项目筛选
                                            fac.AntdSelect(
                                                id="task-project-filter",
                                                placeholder="选择项目",
                                                options=[
                                                    {"label": "全部项目", "value": "all"},
                                                    {"label": "数据处理项目", "value": "1"},
                                                    {"label": "数据分析项目", "value": "2"},
                                                    {"label": "机器学习项目", "value": "3"}
                                                ],
                                                style={"width": "150px"}
                                            ),
                                            
                                            # 新建任务按钮
                                            fac.AntdButton(
                                                id="create-task-button",
                                                "新建任务",
                                                type="primary",
                                                icon=fac.AntdIcon(icon="plus")
                                            )
                                        ]
                                    )
                                ],
                                children=[
                                    # 任务列表表格
                                    html.Div(
                                        id="task-table-container",
                                        children=[
                                            create_task_management_table()
                                        ]
                                    )
                                ]
                            )
                        ]
                    )
                ]
            ),
            
            # 新建/编辑任务模态框
            create_task_modal(),
            
            # 任务历史记录模态框
            create_task_history_modal(),
            
            # 任务日志查看模态框
            create_task_log_modal()
        ]
    )


def create_menu_item(text, icon, is_active=False):
    """创建侧边栏菜单项
    
    参数:
        text (str): 菜单项文本
        icon (str): 菜单项图标
        is_active (bool): 是否为当前活动项
        
    返回:
        html.Div: 菜单项组件
    """
    return html.Div(
        id={"type": "menu-item", "text": text},
        style={
            "padding": "12px 24px",
            "cursor": "pointer",
            "backgroundColor": "#1890ff" if is_active else "transparent",
            "color": "white" if is_active else "#bfbfbf",
            "display": "flex",
            "alignItems": "center",
            "transition": "all 0.3s"
        },
        children=[
            html.Span(className=f"anticon anticon-{icon}", style={"marginRight": "10px"}),
            html.Span(text)
        ]
    )


def create_task_management_table():
    """创建任务管理表格
    
    返回:
        fac.AntdTable: 任务管理表格组件
    """
    return fac.AntdTable(
        id="task-management-table",
        columns=[
            {"title": "任务名称", "dataIndex": "name", "key": "name", "width": 180},
            {"title": "项目", "dataIndex": "project", "key": "project", "width": 150},
            {"title": "Python环境", "dataIndex": "python_env", "key": "python_env", "width": 120},
            {"title": "执行命令", "dataIndex": "command", "key": "command", "width": 200},
            {"title": "调度类型", "dataIndex": "schedule_type", "key": "schedule_type", "width": 100},
            {"title": "状态", "dataIndex": "status", "key": "status", "width": 100},
            {"title": "下次执行时间", "dataIndex": "next_run_time", "key": "next_run_time", "width": 150},
            {"title": "操作", "dataIndex": "action", "key": "action", "width": 200}
        ],
        data=[
            {
                "key": "1",
                "id": "1",
                "name": "数据同步任务",
                "project": "数据处理项目",
                "python_env": "my_env",
                "command": "python sync_data.py",
                "schedule_type": "间隔执行",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#52c41a", "borderRadius": "50%", "marginRight": "4px"}),
                        "活跃中"
                    ]
                ),
                "next_run_time": "2025-10-11 12:30:00",
                "action": [
                    html.Div(
                        id={"type": "task-action", "action": "run", "id": "1"},
                        children=fac.AntdButton("立即执行", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "pause", "id": "1"},
                        children=fac.AntdButton("暂停", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "edit", "id": "1"},
                        children=fac.AntdButton("编辑", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "history", "id": "1"},
                        children=fac.AntdButton("历史", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "delete", "id": "1"},
                        children=fac.AntdButton("删除", type="link", size="small", style={"color": "#f5222d"})
                    )
                ]
            },
            {
                "key": "2",
                "id": "2",
                "name": "报表生成任务",
                "project": "数据分析项目",
                "python_env": "my_env2",
                "command": "cd reports && python generate_report.py",
                "schedule_type": "Cron表达式",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#52c41a", "borderRadius": "50%", "marginRight": "4px"}),
                        "活跃中"
                    ]
                ),
                "next_run_time": "2025-10-11 13:00:00",
                "action": [
                    html.Div(
                        id={"type": "task-action", "action": "run", "id": "2"},
                        children=fac.AntdButton("立即执行", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "pause", "id": "2"},
                        children=fac.AntdButton("暂停", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "edit", "id": "2"},
                        children=fac.AntdButton("编辑", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "history", "id": "2"},
                        children=fac.AntdButton("历史", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "delete", "id": "2"},
                        children=fac.AntdButton("删除", type="link", size="small", style={"color": "#f5222d"})
                    )
                ]
            },
            {
                "key": "3",
                "id": "3",
                "name": "模型训练任务",
                "project": "机器学习项目",
                "python_env": "my_env",
                "command": "python train_model.py --epochs 100",
                "schedule_type": "一次性执行",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#faad14", "borderRadius": "50%", "marginRight": "4px"}),
                        "已暂停"
                    ]
                ),
                "next_run_time": "2025-10-12 08:00:00",
                "action": [
                    html.Div(
                        id={"type": "task-action", "action": "run", "id": "3"},
                        children=fac.AntdButton("立即执行", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "start", "id": "3"},
                        children=fac.AntdButton("启动", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "edit", "id": "3"},
                        children=fac.AntdButton("编辑", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "history", "id": "3"},
                        children=fac.AntdButton("历史", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "task-action", "action": "delete", "id": "3"},
                        children=fac.AntdButton("删除", type="link", size="small", style={"color": "#f5222d"})
                    )
                ]
            }
        ],
        pagination={"pageSize": 10},
        style={"width": "100%"},
        tableLayout="auto"
    )


def create_task_modal():
    """创建任务模态框
    
    返回:
        fac.AntdModal: 任务创建/编辑模态框组件
    """
    return fac.AntdModal(
        id="task-modal",
        title="新建任务",
        centered=True,
        width=800,
        open=False,
        children=[
            fac.AntdForm(
                id="task-form",
                layout="vertical",
                style={"marginBottom": "0"},
                children=[
                    # 基本信息
                    html.Div(style={"marginBottom": "20px"}, children=[
                        html.H3("基本信息", style={"marginBottom": "16px", "fontSize": "16px"}),
                        fac.AntdRow(
                            gutter=16,
                            children=[
                                fac.AntdCol(
                                    span=24,
                                    children=fac.AntdFormItem(
                                        label="任务名称",
                                        children=fac.AntdInput(
                                            id="task-name",
                                            placeholder="请输入任务名称",
                                            allowClear=True,
                                            maxLength=100
                                        )
                                    )
                                ),
                                fac.AntdCol(
                                    span=24,
                                    children=fac.AntdFormItem(
                                        label="任务描述",
                                        children=fac.AntdInput.TextArea(
                                            id="task-description",
                                            placeholder="请输入任务描述（可选）",
                                            allowClear=True,
                                            rows=3,
                                            maxLength=500
                                        )
                                    )
                                ),
                                fac.AntdCol(
                                    xs=24, sm=12,
                                    children=fac.AntdFormItem(
                                        label="选择项目",
                                        children=fac.AntdSelect(
                                            id="task-project",
                                            placeholder="请选择项目",
                                            allowClear=True,
                                            options=[
                                                {"label": "数据处理项目", "value": "1"},
                                                {"label": "数据分析项目", "value": "2"},
                                                {"label": "机器学习项目", "value": "3"}
                                            ],
                                            style={"width": "100%"}
                                        )
                                    )
                                ),
                                fac.AntdCol(
                                    xs=24, sm=12,
                                    children=fac.AntdFormItem(
                                        label="Python虚拟环境",
                                        children=fac.AntdSelect(
                                            id="task-python-env",
                                            placeholder="请选择Python虚拟环境",
                                            options=[
                                                {"label": "my_env (Python 3.9.21)", "value": "1"},
                                                {"label": "my_env2 (Python 3.9.21)", "value": "2"}
                                            ],
                                            style={"width": "100%"}
                                        )
                                    )
                                )
                            ]
                        )
                    ]),
                    
                    # 执行命令
                    html.Div(style={"marginBottom": "20px"}, children=[
                        html.H3("执行命令", style={"marginBottom": "16px", "fontSize": "16px"}),
                        fac.AntdFormItem(
                            label="命令行",
                            children=fac.AntdInput.TextArea(
                                id="task-command",
                                placeholder="请输入要执行的命令，例如：python script.py 或 cd conf/aaa && python 1.py",
                                rows=4,
                                maxLength=1000,
                                style={"fontFamily": "monospace"}
                            )
                        )
                    ]),
                    
                    # 调度设置
                    html.Div(style={"marginBottom": "20px"}, children=[
                        html.H3("调度设置", style={"marginBottom": "16px", "fontSize": "16px"}),
                        fac.AntdRow(
                            gutter=16,
                            children=[
                                fac.AntdCol(
                                    xs=24, sm=12,
                                    children=fac.AntdFormItem(
                                        label="调度类型",
                                        children=fac.AntdSelect(
                                            id="task-schedule-type",
                                            placeholder="请选择调度类型",
                                            options=[
                                                {"label": "立即执行", "value": "immediate"},
                                                {"label": "间隔执行", "value": "interval"},
                                                {"label": "一次性执行", "value": "one-time"},
                                                {"label": "Cron表达式", "value": "cron"}
                                            ],
                                            style={"width": "100%"}
                                        )
                                    )
                                ),
                                # 间隔执行设置
                                html.Div(
                                    id="interval-settings",
                                    style={"display": "none", "width": "100%"},
                                    children=fac.AntdRow(
                                        gutter=16,
                                        children=[
                                            fac.AntdCol(
                                                xs=24, sm=12,
                                                children=fac.AntdFormItem(
                                                    label="间隔时长",
                                                    children=fac.AntdInputNumber(
                                                        id="interval-value",
                                                        min=1,
                                                        style={"width": "100%"}
                                                    )
                                                )
                                            ),
                                            fac.AntdCol(
                                                xs=24, sm=12,
                                                children=fac.AntdFormItem(
                                                    label="时间单位",
                                                    children=fac.AntdSelect(
                                                        id="interval-unit",
                                                        options=[
                                                            {"label": "秒", "value": "seconds"},
                                                            {"label": "分钟", "value": "minutes"},
                                                            {"label": "小时", "value": "hours"},
                                                            {"label": "天", "value": "days"}
                                                        ],
                                                        defaultValue="minutes",
                                                        style={"width": "100%"}
                                                    )
                                                )
                                            )
                                        ]
                                    )
                                ),
                                # 一次性执行设置
                                html.Div(
                                    id="one-time-settings",
                                    style={"display": "none", "width": "100%"},
                                    children=fac.AntdFormItem(
                                        label="执行时间",
                                        children=fac.AntdDatePicker(
                                            id="one-time-date",
                                            showTime=True,
                                            style={"width": "100%"}
                                        )
                                    )
                                ),
                                # Cron表达式设置
                                html.Div(
                                    id="cron-settings",
                                    style={"display": "none", "width": "100%"},
                                    children=fac.AntdFormItem(
                                        label="Cron表达式",
                                        children=[
                                            fac.AntdInput(
                                                id="cron-expression",
                                                placeholder="请输入Cron表达式，例如：0 0 * * *",
                                                style={"width": "100%", "fontFamily": "monospace"}
                                            ),
                                            html.Span("格式: 分 时 日 月 周", style={"color": "#999", "fontSize": "12px", "display": "block", "marginTop": "8px"})
                                        ]
                                    )
                                )
                            ]
                        )
                    ]),
                    
                    # 高级设置
                    html.Div(children=[
                        html.H3("高级设置", style={"marginBottom": "16px", "fontSize": "16px"}),
                        fac.AntdRow(
                            gutter=16,
                            children=[
                                fac.AntdCol(
                                    xs=24, sm=12,
                                    children=fac.AntdFormItem(
                                        label="最大并发实例数",
                                        children=fac.AntdInputNumber(
                                            id="max-instances",
                                            min=1,
                                            max=10,
                                            defaultValue=1,
                                            style={"width": "100%"}
                                        )
                                    )
                                ),
                                fac.AntdCol(
                                    xs=24, sm=12,
                                    children=fac.AntdFormItem(
                                        label="任务标签",
                                        children=fac.AntdInput(
                                            id="task-tags",
                                            placeholder="请输入标签，用逗号分隔",
                                            allowClear=True,
                                            maxLength=100
                                        )
                                    )
                                )
                            ]
                        )
                    ])
                ]
            )
        ],
        footer=[
            fac.AntdButton(id="task-modal-cancel", "取消"),
            fac.AntdButton(id="task-modal-confirm", "确定", type="primary")
        ]
    )


def create_task_history_modal():
    """创建任务历史记录模态框
    
    返回:
        fac.AntdModal: 任务历史记录模态框组件
    """
    return fac.AntdModal(
        id="task-history-modal",
        title="任务执行历史",
        centered=True,
        width=900,
        open=False,
        children=[
            html.Div(
                style={"maxHeight": "600px", "overflowY": "auto"},
                children=[
                    # 筛选条件
                    html.Div(
                        style={"marginBottom": "16px", "display": "flex", "gap": "10px", "alignItems": "center"},
                        children=[
                            fac.AntdSelect(
                                id="history-status-filter",
                                defaultValue="all",
                                options=[
                                    {"label": "全部状态", "value": "all"},
                                    {"label": "成功", "value": "success"},
                                    {"label": "失败", "value": "failed"},
                                    {"label": "运行中", "value": "running"}
                                ],
                                style={"width": "120px"}
                            ),
                            fac.AntdDatePicker.RangePicker(
                                id="history-date-range",
                                style={"width": "300px"}
                            )
                        ]
                    ),
                    
                    # 执行历史表格
                    create_task_history_table()
                ]
            )
        ]
    )


def create_task_history_table():
    """创建任务历史记录表格
    
    返回:
        fac.AntdTable: 任务历史记录表格组件
    """
    return fac.AntdTable(
        id="task-history-table",
        columns=[
            {"title": "执行ID", "dataIndex": "execution_id", "key": "execution_id", "width": 80},
            {"title": "开始时间", "dataIndex": "start_time", "key": "start_time", "width": 180},
            {"title": "结束时间", "dataIndex": "end_time", "key": "end_time", "width": 180},
            {"title": "耗时", "dataIndex": "duration", "key": "duration", "width": 80},
            {"title": "状态", "dataIndex": "status", "key": "status", "width": 100},
            {"title": "操作", "dataIndex": "action", "key": "action", "width": 100}
        ],
        data=[
            {
                "key": "1",
                "execution_id": "101",
                "start_time": "2025-10-11 10:30:00",
                "end_time": "2025-10-11 10:45:30",
                "duration": "15m 30s",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#52c41a", "borderRadius": "50%", "marginRight": "4px"}),
                        "成功"
                    ]
                ),
                "action": [
                    html.Div(
                        id={"type": "execution-action", "action": "logs", "id": "101"},
                        children=fac.AntdButton("查看日志", type="link", size="small")
                    )
                ]
            },
            {
                "key": "2",
                "execution_id": "102",
                "start_time": "2025-10-11 11:15:00",
                "end_time": "",
                "duration": "进行中",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#1890ff", "borderRadius": "50%", "marginRight": "4px"}),
                        "运行中"
                    ]
                ),
                "action": [
                    html.Div(
                        id={"type": "execution-action", "action": "logs", "id": "102"},
                        children=fac.AntdButton("查看日志", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "execution-action", "action": "stop", "id": "102"},
                        children=fac.AntdButton("停止", type="link", size="small", style={"color": "#f5222d"})
                    )
                ]
            },
            {
                "key": "3",
                "execution_id": "103",
                "start_time": "2025-10-11 09:45:00",
                "end_time": "2025-10-11 09:50:23",
                "duration": "5m 23s",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#f5222d", "borderRadius": "50%", "marginRight": "4px"}),
                        "失败"
                    ]
                ),
                "action": [
                    html.Div(
                        id={"type": "execution-action", "action": "logs", "id": "103"},
                        children=fac.AntdButton("查看日志", type="link", size="small")
                    ),
                    html.Div(
                        id={"type": "execution-action", "action": "retry", "id": "103"},
                        children=fac.AntdButton("重试", type="link", size="small")
                    )
                ]
            }
        ],
        pagination={"pageSize": 10},
        style={"width": "100%"},
        tableLayout="auto"
    )


def create_task_log_modal():
    """创建任务日志查看模态框
    
    返回:
        fac.AntdModal: 任务日志查看模态框组件
    """
    return fac.AntdModal(
        id="task-log-modal",
        title="任务运行日志",
        centered=True,
        width=1000,
        open=False,
        children=[
            html.Div(
                style={"maxHeight": "600px", "overflowY": "auto"},
                children=[
                    # 日志筛选和控制
                    html.Div(
                        style={"marginBottom": "16px", "display": "flex", "gap": "10px", "alignItems": "center", "flexWrap": "wrap"},
                        children=[
                            fac.AntdInput(
                                id="log-search-input",
                                placeholder="搜索日志...",
                                style={"width": "200px"},
                                prefix=fac.AntdIcon(icon="search")
                            ),
                            fac.AntdSelect(
                                id="log-level-filter",
                                defaultValue="all",
                                options=[
                                    {"label": "全部级别", "value": "all"},
                                    {"label": "INFO", "value": "info"},
                                    {"label": "WARNING", "value": "warning"},
                                    {"label": "ERROR", "value": "error"}
                                ],
                                style={"width": "120px"}
                            ),
                            fac.AntdButton(
                                id="log-auto-refresh",
                                "自动刷新",
                                type="primary",
                                size="small"
                            ),
                            fac.AntdButton(
                                id="log-download",
                                "下载日志",
                                size="small"
                            )
                        ]
                    ),
                    
                    # 日志内容
                    html.Pre(
                        id="task-log-content",
                        style={
                            "backgroundColor": "#f0f2f5",
                            "padding": "16px",
                            "borderRadius": "4px",
                            "fontFamily": "monospace",
                            "fontSize": "12px",
                            "whiteSpace": "pre-wrap",
                            "wordBreak": "break-all"
                        },
                        children="""[2025-10-11 10:30:00] INFO: 任务开始执行
[2025-10-11 10:30:01] INFO: 连接数据库成功
[2025-10-11 10:30:05] INFO: 开始同步数据表 users
[2025-10-11 10:35:22] INFO: 数据表 users 同步完成，共处理 1000 条记录
[2025-10-11 10:35:23] INFO: 开始同步数据表 orders
[2025-10-11 10:45:15] INFO: 数据表 orders 同步完成，共处理 5000 条记录
[2025-10-11 10:45:20] INFO: 断开数据库连接
[2025-10-11 10:45:30] INFO: 任务执行完成，耗时: 15 分钟 30 秒"""
                    )
                ]
            )
        ]
    )


# 设置应用布局
app.layout = create_layout()

# 定义菜单项点击回调
@callback(
    Output("page-title", "children"),
    [Input({"type": "menu-item", "text": ALL}, "n_clicks")],
    [State({"type": "menu-item", "text": ALL}, "id")]
)
def handle_menu_click(n_clicks, menu_ids):
    """处理侧边栏菜单项点击事件
    
    参数:
        n_clicks: 菜单项点击次数列表
        menu_ids: 菜单项ID列表
        
    返回:
        str: 页面标题
    """
    if any(n_clicks):
        # 获取被点击的菜单项
        clicked_index = next(i for i, n in enumerate(n_clicks) if n)
        return menu_ids[clicked_index]["text"]
    return "定时任务"

# 定义新建任务按钮点击回调
@callback(
    Output("task-modal", "open"),
    Output("task-modal", "title"),
    [Input("create-task-button", "n_clicks"),
     Input({"type": "task-action", "action": "edit", "id": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def open_task_modal(create_clicks, edit_clicks):
    """打开任务模态框
    
    参数:
        create_clicks: 新建任务按钮点击次数
        edit_clicks: 编辑任务按钮点击次数列表
        
    返回:
        tuple: (模态框显示状态, 模态框标题)
    """
    ctx = callback_context
    if not ctx.triggered:
        return False, "新建任务"
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "create-task-button":
        # 打开新建任务模态框
        return True, "新建任务"
    elif isinstance(trigger_id, str) and trigger_id.startswith("{"):
        # 打开编辑任务模态框
        return True, "编辑任务"
        
    return False, "新建任务"

# 定义任务模态框取消按钮回调
@callback(
    Output("task-modal", "open", allow_duplicate=True),
    [Input("task-modal-cancel", "n_clicks")],
    prevent_initial_call=True
)
def close_task_modal(n_clicks):
    """关闭任务模态框
    
    参数:
        n_clicks: 取消按钮点击次数
        
    返回:
        bool: 模态框显示状态
    """
    return False

# 定义任务模态框确定按钮回调
@callback(
    Output("task-modal", "open", allow_duplicate=True),
    [Input("task-modal-confirm", "n_clicks")],
    prevent_initial_call=True
)
def confirm_task_modal(n_clicks):
    """确认任务模态框
    
    参数:
        n_clicks: 确定按钮点击次数
        
    返回:
        bool: 模态框显示状态
    """
    # 这里可以添加任务创建或编辑的逻辑
    return False

# 定义调度类型切换回调
@callback(
    [Output("interval-settings", "style"),
     Output("one-time-settings", "style"),
     Output("cron-settings", "style")],
    [Input("task-schedule-type", "value")],
    prevent_initial_call=True
)
def show_schedule_settings(schedule_type):
    """根据调度类型显示对应的设置区域
    
    参数:
        schedule_type: 调度类型
        
    返回:
        tuple: (间隔执行设置样式, 一次性执行设置样式, Cron表达式设置样式)
    """
    interval_style = {"display": "none", "width": "100%"}
    one_time_style = {"display": "none", "width": "100%"}
    cron_style = {"display": "none", "width": "100%"}
    
    if schedule_type == "interval":
        interval_style["display"] = "block"
    elif schedule_type == "one-time":
        one_time_style["display"] = "block"
    elif schedule_type == "cron":
        cron_style["display"] = "block"
    
    return interval_style, one_time_style, cron_style

# 定义任务历史按钮点击回调
@callback(
    Output("task-history-modal", "open"),
    [Input({"type": "task-action", "action": "history", "id": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def open_task_history_modal(history_clicks):
    """打开任务历史记录模态框
    
    参数:
        history_clicks: 历史记录按钮点击次数列表
        
    返回:
        bool: 模态框显示状态
    """
    if any(history_clicks):
        return True
    return False

# 定义任务日志按钮点击回调
@callback(
    Output("task-log-modal", "open"),
    [Input({"type": "execution-action", "action": "logs", "id": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def open_task_log_modal(logs_clicks):
    """打开任务日志查看模态框
    
    参数:
        logs_clicks: 日志查看按钮点击次数列表
        
    返回:
        bool: 模态框显示状态
    """
    if any(logs_clicks):
        return True
    return False


if __name__ == "__main__":
    app.run(debug=False, port=8050)