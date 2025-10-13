#!/usr/bin/env python3
"""
测试脚本：验证目录创建功能是否已被禁用

此脚本用于测试我们对项目代码的修改是否生效，即执行程序时不会自动创建
envs、projects、python_envs、python_versions等目录。
"""
import os
import sys
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 记录当前目录结构
def record_current_dirs():
    """记录当前目录中的所有子目录"""
    dirs = []
    for item in os.listdir(project_root):
        item_path = os.path.join(project_root, item)
        if os.path.isdir(item_path) and not item.startswith('.'):
            dirs.append(item)
    return dirs

def main():
    """主函数：测试目录创建"""
    # 记录初始目录结构
    initial_dirs = record_current_dirs()
    print(f"初始目录结构: {initial_dirs}")
    
    # 导入可能会创建目录的模块
    print("\n尝试导入模块以触发可能的目录创建...")
    
    try:
        # 导入env_manager模块
        import app.virtual_envs.env_manager
        print("- 已导入app.virtual_envs.env_manager")
    except Exception as e:
        print(f"- 导入app.virtual_envs.env_manager失败: {str(e)}")
    
    try:
        # 导入tools模块
        import app.utils.tools
        print("- 已导入app.utils.tools")
    except Exception as e:
        print(f"- 导入app.utils.tools失败: {str(e)}")
    
    try:
        # 导入project_manager模块
        import app.projects.project_manager
        print("- 已导入app.projects.project_manager")
    except Exception as e:
        print(f"- 导入app.projects.project_manager失败: {str(e)}")
    
    try:
        # 导入version_manager模块
        import app.python_versions.version_manager
        print("- 已导入app.python_versions.version_manager")
    except Exception as e:
        print(f"- 导入app.python_versions.version_manager失败: {str(e)}")
    
    try:
        # 导入envs模块
        import envs
        print("- 已导入envs")
    except Exception as e:
        print(f"- 导入envs失败: {str(e)}")
    
    # 记录导入后的目录结构
    after_import_dirs = record_current_dirs()
    print(f"\n导入后的目录结构: {after_import_dirs}")
    
    # 检查是否有新目录创建
    new_dirs = set(after_import_dirs) - set(initial_dirs)
    if new_dirs:
        print(f"\n发现新创建的目录: {new_dirs}")
    else:
        print("\n✓ 没有发现新创建的目录，修改生效！")
    
    print("\n测试完成。")

if __name__ == '__main__':
    main()