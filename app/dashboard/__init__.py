# -*- coding: utf-8 -*-
"""仪表盘模块

提供实时的系统资源使用情况监控，帮助及时了解系统的运行状态"""

# 导入pages模块，确保所有页面路由被正确注册
from . import pages

# 从pages模块中导入DashboardUI类，便于外部直接使用
from .pages import DashboardUI

__all__ = ['pages', 'DashboardUI']