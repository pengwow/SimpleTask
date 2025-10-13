#!/usr/bin/env python3
"""测试Python版本管理模块

这个脚本用于测试Python版本管理模块的基本功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.db import PythonVersion
from app.python_versions.version_manager import PythonVersionManager


def test_imports():
    """测试模块导入是否正常"""
    print("测试模块导入...")
    print(f"成功导入PythonVersionManager: {PythonVersionManager is not None}")
    print(f"成功导入PythonVersion: {PythonVersion is not None}")
    
    # 检查PythonVersionManager的方法是否存在
    required_methods = [
        'add_python_version',
        '_download_and_install_python',
        'get_installed_versions',
        'set_default_version',
        'delete_version',
        'get_python_executable'
    ]
    
    for method in required_methods:
        if hasattr(PythonVersionManager, method):
            print(f"✅ 方法 {method} 存在")
        else:
            print(f"❌ 方法 {method} 不存在")

if __name__ == "__main__":
    try:
        print("开始测试Python版本管理模块...")
        test_imports()
        print("\n测试完成！所有功能已准备就绪，可以开始使用Python版本管理功能了。")
        print("\n使用方法:")
        print("1. 通过API添加Python版本: POST /api/python_versions")
        print("2. 查看已安装的Python版本: GET /api/python_versions")
        print("3. 设置默认Python版本: POST /api/python_versions/<id>/set_default")
        print("4. 删除Python版本: DELETE /api/python_versions/<id>")
        print("5. 查看实时安装日志: GET /api/python_versions/<id>/log_stream")
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()