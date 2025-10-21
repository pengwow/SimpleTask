#!/usr/bin/env python3
"""
数据库初始化脚本

用于创建数据库表结构和初始数据
"""
import os
import sys
from app.db.database import engine, Base, get_db
from app.db.models import (
    MirrorSource, PythonEnv, EnvLog, PythonVersion,
    ProjectTag, Project, Task, TaskExecution, TaskLog
)
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('init_db')

def create_tables():
    """
    创建数据库表结构
    
    基于SQLAlchemy模型创建所有数据库表
    """
    try:
        logger.info("开始创建数据库表结构...")
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表结构创建成功")
        return True
    except Exception as e:
        logger.error(f"创建数据库表结构失败: {str(e)}")
        return False

def insert_initial_data():
    """
    插入初始数据
    
    向数据库中插入一些基础的初始数据
    """
    try:
        logger.info("开始插入初始数据...")
        db = next(get_db())
        
        # 检查是否已有数据
        existing_mirrors = db.query(MirrorSource).count()
        if existing_mirrors > 0:
            logger.info("数据库中已存在初始数据，跳过插入")
            return True
        
        # 添加默认的Python镜像源
        default_mirrors = [
            {
                'name': '官方源',
                'url': 'https://pypi.org/simple',
                'is_active': False
            },
            {
                'name': '阿里云',
                'url': 'https://mirrors.aliyun.com/pypi/simple/',
                'is_active': True
            },
            {
                'name': '清华源',
                'url': 'https://pypi.tuna.tsinghua.edu.cn/simple/',
                'is_active': False
            }
        ]
        
        for mirror_data in default_mirrors:
            mirror = MirrorSource(**mirror_data)
            db.add(mirror)
        
        # 添加默认标签
        default_tags = ['Web开发', '数据科学', '自动化测试', 'DevOps', '机器学习']
        for tag_name in default_tags:
            tag = ProjectTag(name=tag_name)
            db.add(tag)
        
        db.commit()
        logger.info("初始数据插入成功")
        return True
    except Exception as e:
        logger.error(f"插入初始数据失败: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()

def drop_tables():
    """
    删除所有数据库表
    
    警告：这将删除所有数据，请谨慎使用
    """
    try:
        logger.warning("正在删除所有数据库表...")
        Base.metadata.drop_all(bind=engine)
        logger.warning("所有数据库表已删除")
        return True
    except Exception as e:
        logger.error(f"删除数据库表失败: {str(e)}")
        return False

def main():
    """
    主函数
    
    根据命令行参数执行相应操作
    """
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == 'drop':
            # 删除所有表
            if drop_tables():
                print("\n数据库表已全部删除")
                sys.exit(0)
            else:
                print("\n数据库表删除失败")
                sys.exit(1)
        else:
            print(f"\n未知参数: {sys.argv[1]}")
            print("使用方法:")
            print("  python init_db.py          # 创建表并插入初始数据")
            print("  python init_db.py drop     # 删除所有表（危险操作）")
            sys.exit(1)
    
    # 正常初始化流程
    print("\n开始初始化数据库...")
    
    # 创建表结构
    if not create_tables():
        print("\n数据库初始化失败")
        sys.exit(1)
    
    # 插入初始数据
    if not insert_initial_data():
        print("\n数据库初始化失败")
        sys.exit(1)
    
    print("\n数据库初始化成功！")
    sys.exit(0)

if __name__ == '__main__':
    main()