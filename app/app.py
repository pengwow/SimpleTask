#!/usr/bin/env python3
"""Python虚拟环境管理系统主入口

提供完整的Python虚拟环境管理、任务管理、日志管理等功能
"""
import os
import sys
import logging

# 添加项目根目录到Python路径，确保正确解析所有导入
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入API路由
from app.api.routes import app

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('python_envs.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('python_envs')

def main():
    """主函数，初始化并启动应用"""
    try:
        
        # 启动Flask应用
        logger.info("启动Python虚拟环境管理服务...")
        logger.info("服务将在 http://localhost:5001 启动")
        logger.info("按 Ctrl+C 停止服务")
        app.run(host='0.0.0.0', port=5001, debug=True)
    except Exception as e:
        logger.error(f"服务启动失败: {str(e)}")
        raise

if __name__ == '__main__':
    main()