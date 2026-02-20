import pytest
from playwright.sync_api import Page, expect

# 注意：运行此测试需要先启动后端服务
# 使用 pytest tests/e2e/test_ui_flow.py 运行

BASE_URL = "http://localhost:5001/gui"

@pytest.mark.skip(reason="Requires running backend server")
def test_dashboard_load(page: Page):
    """测试仪表板加载"""
    page.goto(f"{BASE_URL}/dashboard")
    expect(page).to_have_title("任务管理系统")
    expect(page.get_by_text("系统概览")).to_be_visible()
    expect(page.get_by_text("虚拟环境")).to_be_visible()
    expect(page.get_by_text("活跃任务")).to_be_visible()

@pytest.mark.skip(reason="Requires running backend server")
def test_navigation(page: Page):
    """测试导航功能"""
    page.goto(f"{BASE_URL}/dashboard")
    
    # 导航到虚拟环境页面
    page.get_by_role("button", name="虚拟环境").click()
    expect(page.get_by_text("虚拟环境管理")).to_be_visible()
    
    # 导航到任务管理页面
    page.get_by_role("button", name="任务管理").click()
    expect(page.get_by_text("任务管理", exact=True)).to_be_visible()
    
    # 导航到项目管理页面
    page.get_by_role("button", name="项目管理").click()
    expect(page.get_by_text("项目管理", exact=True)).to_be_visible()

@pytest.mark.skip(reason="Requires running backend server")
def test_create_env_dialog(page: Page):
    """测试创建环境对话框"""
    page.goto(f"{BASE_URL}/environments")
    
    # 点击创建按钮
    page.get_by_role("button", name="创建新环境").click()
    
    # 验证对话框显示
    expect(page.get_by_text("创建新虚拟环境")).to_be_visible()
    expect(page.get_by_label("环境名称")).to_be_visible()
    expect(page.get_by_label("Python版本")).to_be_visible()
    
    # 关闭对话框
    page.get_by_role("button", name="取消").click()
    expect(page.get_by_text("创建新虚拟环境")).not_to_be_visible()

@pytest.mark.skip(reason="Requires running backend server")
def test_create_task_dialog(page: Page):
    """测试创建任务对话框"""
    page.goto(f"{BASE_URL}/tasks")
    
    # 点击创建按钮
    page.get_by_role("button", name="创建新任务").click()
    
    # 验证对话框显示
    expect(page.get_by_text("创建新任务")).to_be_visible()
    expect(page.get_by_label("任务名称")).to_be_visible()
    
    # 关闭对话框
    page.get_by_role("button", name="取消").click()
    expect(page.get_by_text("创建新任务")).not_to_be_visible()
