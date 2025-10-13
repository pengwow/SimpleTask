import dash
from dash import html, dcc
import feffery_antd_components as fac
from dash.dependencies import Input, Output, State

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
                            create_menu_item("仪表盘", "dashboard", True),
                            create_menu_item("定时任务", "clock-circle"),
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
                                    html.Span("仪表盘", style={"fontSize": "16px", "fontWeight": "bold"})
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
                            # 统计卡片区域
                            html.Div(
                                style={
                                    "display": "flex",
                                    "gap": "16px",
                                    "marginBottom": "24px"
                                },
                                children=[
                                    create_stat_card("总项目", "5", "project", "#1890ff"),
                                    create_stat_card("活跃任务", "12", "clock-circle", "#52c41a"),
                                    create_stat_card("环境数", "3", "code-square", "#faad14"),
                                    create_stat_card("用户数", "8", "user", "#f5222d")
                                ]
                            ),
                            
                            # 图表和表格区域
                            html.Div(
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1fr 1fr",
                                    "gap": "16px",
                                    "marginBottom": "24px"
                                },
                                children=[
                                    # 图表卡片
                                    fac.AntdCard(
                                        title="任务执行统计",
                                        hoverable=True,
                                        style={"height": "300px"},
                                        children=[
                                            html.Div(style={"height": "240px", "display": "flex", "alignItems": "center", "justifyContent": "center"},
                                                children=[html.Span("图表区域")]
                                            )
                                        ]
                                    ),
                                    
                                    # 环境列表卡片
                                    fac.AntdCard(
                                        title="Python环境",
                                        hoverable=True,
                                        style={"height": "300px"},
                                        extra=fac.AntdButton("新建环境", type="primary", size="small"),
                                        children=[
                                            create_env_table()
                                        ]
                                    )
                                ]
                            ),
                            
                            # 任务列表区域
                            fac.AntdCard(
                                title="最近任务",
                                hoverable=True,
                                extra=[
                                    fac.AntdSelect(
                                        defaultValue="all",
                                        options=[
                                            {"label": "全部状态", "value": "all"},
                                            {"label": "运行中", "value": "running"},
                                            {"label": "已完成", "value": "completed"},
                                            {"label": "失败", "value": "failed"}
                                        ],
                                        style={"width": "120px"}
                                    ),
                                    fac.AntdButton("新建任务", type="primary", size="small", style={"marginLeft": "10px"})
                                ],
                                children=[
                                    create_task_table()
                                ]
                            )
                        ]
                    )
                ]
            )
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


def create_stat_card(title, value, icon, color):
    """创建统计卡片
    
    参数:
        title (str): 卡片标题
        value (str): 卡片数值
        icon (str): 卡片图标
        color (str): 卡片颜色
        
    返回:
        fac.AntdCard: 统计卡片组件
    """
    return fac.AntdCard(
        hoverable=True,
        style={
            "flex": 1,
            "display": "flex",
            "alignItems": "center",
            "padding": "16px"
        },
        children=[
            html.Div(
                style={
                    "width": "64px",
                    "height": "64px",
                    "backgroundColor": f"{color}20",
                    "borderRadius": "8px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "marginRight": "16px"
                },
                children=[
                    html.Span(className=f"anticon anticon-{icon}", style={"fontSize": "24px", "color": color})
                ]
            ),
            html.Div(
                children=[
                    html.H3(value, style={"margin": 0, "fontSize": "24px"}),
                    html.Span(title, style={"color": "#666"})
                ]
            )
        ]
    )


def create_env_table():
    """创建环境列表表格
    
    返回:
        fac.AntdTable: 环境列表表格组件
    """
    return fac.AntdTable(
        columns=[
            {"title": "环境名称", "dataIndex": "name", "key": "name", "width": 120},
            {"title": "Python版本", "dataIndex": "version", "key": "version", "width": 100},
            {"title": "状态", "dataIndex": "status", "key": "status", "width": 80},
            {"title": "操作", "dataIndex": "action", "key": "action", "width": 80}
        ],
        data=[
            {
                "key": "1",
                "name": "my_env",
                "version": "3.9.21",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#52c41a", "borderRadius": "50%", "marginRight": "4px"}),
                        "就绪"
                    ]
                ),
                "action": fac.AntdButton("管理", type="link", size="small")
            },
            {
                "key": "2",
                "name": "my_env2",
                "version": "3.9.21",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#52c41a", "borderRadius": "50%", "marginRight": "4px"}),
                        "就绪"
                    ]
                ),
                "action": fac.AntdButton("管理", type="link", size="small")
            }
        ],
        pagination=False,
        size="small",
        style={"width": "100%"},
        tableLayout="auto"
    )


def create_task_table():
    """创建任务列表表格
    
    返回:
        fac.AntdTable: 任务列表表格组件
    """
    return fac.AntdTable(
        columns=[
            {"title": "任务名称", "dataIndex": "name", "key": "name", "width": 150},
            {"title": "项目", "dataIndex": "project", "key": "project", "width": 120},
            {"title": "环境", "dataIndex": "env", "key": "env", "width": 100},
            {"title": "状态", "dataIndex": "status", "key": "status", "width": 80},
            {"title": "开始时间", "dataIndex": "start_time", "key": "start_time", "width": 150},
            {"title": "操作", "dataIndex": "action", "key": "action", "width": 120}
        ],
        data=[
            {
                "key": "1",
                "name": "数据同步任务",
                "project": "数据处理项目",
                "env": "my_env",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#52c41a", "borderRadius": "50%", "marginRight": "4px"}),
                        "已完成"
                    ]
                ),
                "start_time": "2025-10-11 10:30:00",
                "action": [
                    fac.AntdButton("查看日志", type="link", size="small"),
                    fac.AntdButton("重试", type="link", size="small")
                ]
            },
            {
                "key": "2",
                "name": "报表生成任务",
                "project": "数据分析项目",
                "env": "my_env2",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#1890ff", "borderRadius": "50%", "marginRight": "4px"}),
                        "运行中"
                    ]
                ),
                "start_time": "2025-10-11 11:15:00",
                "action": [
                    fac.AntdButton("查看日志", type="link", size="small"),
                    fac.AntdButton("停止", type="link", size="small", style={"color": "#f5222d"})
                ]
            },
            {
                "key": "3",
                "name": "模型训练任务",
                "project": "机器学习项目",
                "env": "my_env",
                "status": html.Span(
                    [
                        html.Span(style={"display": "inline-block", "width": "8px", "height": "8px", "backgroundColor": "#f5222d", "borderRadius": "50%", "marginRight": "4px"}),
                        "失败"
                    ]
                ),
                "start_time": "2025-10-11 09:45:00",
                "action": [
                    fac.AntdButton("查看日志", type="link", size="small"),
                    fac.AntdButton("重试", type="link", size="small")
                ]
            }
        ],
        pagination={"pageSize": 5},
        style={"width": "100%"},
        tableLayout="auto"
    )


# 设置应用布局
app.layout = create_layout()

# 定义回调函数 - 这里可以添加交互逻辑


if __name__ == "__main__":
    app.run(debug=False, port=8050)