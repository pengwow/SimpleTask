import dash
from dash import html
import feffery_antd_components as fac
from dash.dependencies import Input, Output, State

# 实例化Dash应用对象
app = dash.Dash(__name__)

# 添加自定义CSS样式
app.config.external_stylesheets = ['https://cdn.jsdelivr.net/npm/antd@5.0.0/dist/reset.css']

# 创建登录页面布局
app.layout = html.Div(
    style={
        "height": "100vh",
        "background": "linear-gradient(135deg, #667eea 0%, #764ba2 100%)",
        "display": "flex",
        "justifyContent": "center",
        "alignItems": "center",
        "margin": 0,
        "padding": 0,
        "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    },
    children=[
        fac.AntdCard(
            [
                # 登录表单标题
                html.Div(
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center"
                    },
                    children=[
                        html.Img(
                            src="https://via.placeholder.com/80x80?text=Logo",
                            style={
                                "display": "block",
                                "margin": "0 auto 16px",
                                "width": "80px",
                                "height": "80px",
                                "borderRadius": "40px"
                            }
                        ),
                        html.H2(
                            "SimpleTask",
                            style={
                                "textAlign": "center",
                                "color": "#1890ff",
                                "marginBottom": "24px",
                                "fontWeight": "bold"
                            }
                        )
                    ]
                ),
                
                # 登录表单
                fac.AntdForm(
                    [
                        fac.AntdFormItem(
                            fac.AntdInput(
                                id="username",
                                placeholder="请输入用户名",
                                prefix=fac.AntdIcon(icon="user"),
                                style={"width": "100%"}
                            ),
                            label="用户名",
                            labelCol={"span": 24},
                            wrapperCol={"span": 24}
                        ),
                        fac.AntdFormItem(
                            fac.AntdInput(
                                id="password",
                                placeholder="请输入密码",
                                prefix=fac.AntdIcon(icon="lock"),
                                passwordUseMd5=False,
                                style={"width": "100%"}
                            ),
                            label="密码",
                            labelCol={"span": 24},
                            wrapperCol={"span": 24}
                        ),
                        fac.AntdFormItem(
                            [
                                fac.AntdCheckbox(id="remember-me", label="记住我")
                            ],
                            wrapperCol={"span": 24, "offset": 0}
                        ),
                        fac.AntdFormItem(
                            html.Button(
                                "登录",
                                id="login-button",
                                className="ant-btn ant-btn-primary",
                                style={"width": "100%", "height": "40px", "fontSize": "16px"}
                            ),
                            wrapperCol={"span": 24, "offset": 0}
                        )
                    ],
                    layout="vertical",
                    style={"marginBottom": 10, "width": "100%"}
                ),
                
                # 错误信息显示区域
                html.Div(
                    id="login-error",
                    style={"display": "none", "textAlign": "center", "marginTop": "10px"}
                )
            ],
            hoverable=True,
            style={
                "width": 400,
                "padding": "30px",
                "borderRadius": "8px",
                "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.15)",
                "backgroundColor": "rgba(255, 255, 255, 0.95)"
            }
        )
    ]
)


# 定义登录回调函数
@app.callback(
    [Output("login-error", "children"),
     Output("login-error", "style")],
    [Input("login-button", "n_clicks")],
    [State("username", "value"),
     State("password", "value"),
     State("remember-me", "checked")]
)
def handle_login(n_clicks, username, password, remember_me):
    """
    处理登录请求的回调函数
    
    参数:
        n_clicks: 登录按钮点击次数
        username: 输入的用户名
        password: 输入的密码
        remember_me: 是否记住用户
    
    返回值:
        tuple: (错误信息内容, 错误信息样式)
    """
    # 检查是否有点击事件且用户名和密码不为空
    if n_clicks is not None:
        if not username or not password:
            return (
                "用户名和密码不能为空",
                {"display": "block", "color": "#f5222d", "textAlign": "center", "marginTop": "10px"}
            )
        
        # 这里可以添加实际的登录验证逻辑
        # 目前仅作为示例，使用简单的用户名密码验证
        if username == "admin" and password == "admin123":
            # 登录成功，可以在这里添加跳转到其他页面的逻辑
            return (
                "登录成功！",
                {"display": "block", "color": "#52c41a", "textAlign": "center", "marginTop": "10px"}
            )
        else:
            return (
                "用户名或密码错误",
                {"display": "block", "color": "#f5222d", "textAlign": "center", "marginTop": "10px"}
            )
    
    # 初始状态不显示错误信息
    return "", {"display": "none"}


if __name__ == "__main__":
    # 启动应用，设置debug=True以便开发调试
    app.run(debug=False, host='0.0.0.0', port=8050)