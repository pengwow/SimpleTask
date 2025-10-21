#!/usr/bin/env python3
"""测试数据库连接修复

验证将db = get_db()改为db = next(get_db())后的修复效果
"""
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db import get_db
from app.db.models import MirrorSource

def test_db_connection():
    """测试数据库连接是否正常工作"""
    print("测试数据库连接修复...")
    
    try:
        # 测试1: 获取活跃镜像源
        from app.utils.tools import get_active_mirror
        print("测试获取活跃镜像源...")
        mirror = get_active_mirror()
        print(f"成功获取镜像源: {mirror.name if mirror else 'None'}")
        
        # 测试2: 直接使用数据库会话
        print("测试直接使用数据库会话...")
        db = next(get_db())
        try:
            # 尝试查询
            mirrors = db.query(MirrorSource).limit(1).all()
            print(f"成功查询数据库，找到 {len(mirrors)} 个镜像源")
        finally:
            db.close()
        
        print("\n✅ 数据库连接修复测试通过！")
        print("修复总结：")
        print("1. 将所有 db = get_db() 改为 db = next(get_db())")
        print("2. 这样可以正确获取数据库会话对象，而不是生成器本身")
        print("3. 修复了 'generator' object has no attribute 'rollback' 错误")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_db_connection()