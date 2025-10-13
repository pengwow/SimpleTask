#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本

用于初始化Python虚拟环境管理模块的数据库，创建必要的表结构和初始数据。
这个脚本可以在应用首次运行前单独执行，也可以通过主程序自动调用。
"""
import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径，确保正确解析所有导入
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入数据库模型
from app.models.db import db, MirrorSource, PythonEnv, EnvLog
from app.utils.tools import ENV_ROOT_DIR


def init_database():
    """
    初始化数据库，创建必要的表结构和默认数据
    
    创建虚拟环境根目录、初始化数据库连接、创建所有表结构、添加默认镜像源和示例环境
    """
    # 确保虚拟环境根目录存在
    # 注释掉自动创建目录的代码，按用户要求不自动创建目录
    # os.makedirs(ENV_ROOT_DIR, exist_ok=True)
    
    # 连接数据库
    print("正在初始化数据库: simpletask.db")
    db.connect()
    
    # 创建所有表结构
    print("创建数据库表结构...")
    db.create_tables([MirrorSource, PythonEnv, EnvLog])
    
    # 添加默认镜像源
    try:
        # 检查是否已有镜像源
        existing_sources = MirrorSource.select().count()
        if existing_sources == 0:
            # 添加国内常用的PyPI镜像源
            MirrorSource.create(
                name="阿里云",
                url="https://mirrors.aliyun.com/pypi/simple/",
                is_active=True  # 默认使用阿里云镜像源
            )
            MirrorSource.create(
                name="清华大学",
                url="https://pypi.tuna.tsinghua.edu.cn/simple/"
            )
            MirrorSource.create(
                name="官方源",
                url="https://pypi.org/simple/"
            )
            print("✓ 成功添加默认镜像源")
        else:
            print("✓ 镜像源已存在，跳过添加")
    except Exception as e:
        print(f"✗ 添加镜像源失败: {e}")
        
    # 添加示例环境（可选）
    try:
        # 检查是否已有环境
        existing_envs = PythonEnv.select().count()
        if existing_envs == 0:
            # 获取默认镜像源
            default_mirror = MirrorSource.get(MirrorSource.is_active == True)
            
            # 创建一个示例Python环境
            PythonEnv.create(
                name="sample_env",
                python_version="3.9",
                path="",  # 示例环境不实际创建目录
                mirror_source=default_mirror
            )
            print(f"✓ 成功创建示例环境: sample_env")
        else:
            print("✓ 环境已存在，跳过创建示例环境")
    except Exception as e:
        print(f"✗ 创建示例环境失败: {e}")
    
    # 关闭数据库连接
    db.close()
    print("数据库初始化完成！")


def clear_database():
    """
    清空数据库，删除所有表结构
    警告：此操作将删除所有数据，请谨慎使用！
    """
    # 连接数据库
    db.connect()
    
    print("正在清空数据库")
    
    # 删除所有表结构
    db.drop_tables([MirrorSource, PythonEnv, EnvLog], safe=True)
    print("✓ 成功清空数据库")
    
    # 关闭数据库连接
    db.close()


def main():
    """
    主函数，根据命令行参数执行相应的操作
    """
    # 解析命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == '--clear':
            clear_database()
        else:
            print("用法: python init_db.py [--clear]")
            print("  --clear: 清空数据库，删除所有表结构")
            sys.exit(1)
    else:
        # 默认执行初始化
        init_database()


if __name__ == '__main__':
    main()