#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试项目管理模块的核心功能

用于测试ProjectManager类的主要功能是否正常工作
"""

import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入项目管理模块和数据库模型
from app.db import get_db, Project, ProjectTag, ProjectToTag
from app.projects.project_manager import ProjectManager, PROJECTS_ROOT
from app.utils.tools import ensure_dir_exists

class TestProjectManager(unittest.TestCase):
    """项目管理模块测试类"""
    
    def setUp(self):
        """测试前的初始化工作"""
        # 创建临时目录作为项目根目录
        self.temp_projects_root = tempfile.mkdtemp()
        self.original_projects_root = PROJECTS_ROOT
        
        # 临时修改项目根目录
        ProjectManager.PROJECTS_ROOT = self.temp_projects_root
        
        # 确保临时目录存在
        ensure_dir_exists(self.temp_projects_root)
        
        # 创建测试数据
        self._create_test_data()
    
    def tearDown(self):
        """测试后的清理工作"""
        # 恢复原始项目根目录
        ProjectManager.PROJECTS_ROOT = self.original_projects_root
        
        # 删除临时目录
        shutil.rmtree(self.temp_projects_root, ignore_errors=True)
    
    def _create_test_data(self):
        """创建测试数据"""
        # 注意：这里不实际创建数据库记录，仅测试核心功能
        pass
        
    def _get_db(self):
        """获取数据库会话"""
        return get_db()
    
    def test_create_project(self):
        """测试创建项目功能
        
        验证项目创建功能是否正常工作，包括参数验证、项目目录创建等
        """
        print("\n测试创建项目功能...")
        
        # 创建一个测试项目
        result = ProjectManager.create_project(
            name="test_project",
            description="测试项目",
            work_path='/',
            source_type='zip',
            tags=["测试", "开发"]
        )
        
        # 检查创建结果
        self.assertTrue(result['success'])
        self.assertIn('id', result['data'])
        
        # 检查项目是否存在
        project_id = result['data']['id']
        db = next(self._get_db())
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            self.assertIsNotNone(project)
            self.assertEqual(project.name, "test_project")
            self.assertEqual(project.description, "测试项目")
        finally:
            db.close()
        
        print("✓ 创建项目功能测试通过")
    
    def test_update_project(self):
        """测试更新项目功能
        
        验证项目更新功能是否正常工作，包括名称、描述、工作路径和标签的更新
        """
        print("\n测试更新项目功能...")
        
        # 先创建一个测试项目
        create_result = ProjectManager.create_project(
            name="update_test",
            description="待更新项目"
        )
        self.assertTrue(create_result['success'])
        
        project_id = create_result['data']['id']
        
        # 更新项目信息
        update_result = ProjectManager.update_project(
            project_id=project_id,
            name="updated_project",
            description="已更新的项目",
            work_path='/src',
            tags=["更新", "测试"]
        )
        
        # 检查更新结果
        self.assertTrue(update_result['success'])
        
        # 验证项目信息是否已更新
        project = Project.get_by_id(project_id)
        self.assertEqual(project.name, "updated_project")
        self.assertEqual(project.description, "已更新的项目")
        self.assertEqual(project.work_path, '/src')
        
        # 验证标签是否已更新
        project_tags = [tag.name for tag in project.tags]
        self.assertIn("更新", project_tags)
        self.assertIn("测试", project_tags)
        
        print("✓ 更新项目功能测试通过")
    
    def test_delete_project(self):
        """测试删除项目功能
        
        验证项目删除功能是否正常工作，包括项目记录删除和项目目录清理
        """
        print("\n测试删除项目功能...")
        
        # 先创建一个测试项目
        create_result = ProjectManager.create_project(
            name="delete_test",
            description="待删除项目"
        )
        self.assertTrue(create_result['success'])
        
        project_id = create_result['data']['id']
        
        # 创建项目目录和测试文件
        project_path = os.path.join(self.temp_projects_root, "delete_test")
        os.makedirs(project_path, exist_ok=True)
        with open(os.path.join(project_path, "test.txt"), "w") as f:
            f.write("test content")
        
        # 删除项目
        delete_result = ProjectManager.delete_project(project_id)
        
        # 检查删除结果
        self.assertTrue(delete_result['success'])
        
        # 验证项目是否已从数据库中删除
        with self.assertRaises(Project.DoesNotExist):
            Project.get_by_id(project_id)
        
        # 验证项目目录是否已删除
        self.assertFalse(os.path.exists(project_path))
        
        print("✓ 删除项目功能测试通过")
    
    def test_get_projects(self):
        """测试获取项目列表功能
        
        验证获取项目列表功能是否正常工作，包括分页、搜索和标签筛选
        """
        print("\n测试获取项目列表功能...")
        
        # 创建几个测试项目
        for i in range(5):
            tags = ["测试", f"项目{i+1}"] if i % 2 == 0 else ["生产"]
            ProjectManager.create_project(
                name=f"project_{i+1}",
                description=f"测试项目 {i+1}",
                tags=tags
            )
        
        # 获取项目列表
        result = ProjectManager.get_projects(page=1, per_page=10)
        
        # 检查结果
        self.assertTrue(result['success'])
        self.assertIn('projects', result['data'])
        self.assertIn('pagination', result['data'])
        
        # 验证项目数量
        self.assertEqual(len(result['data']['projects']), 5)
        
        # 测试搜索功能
        search_result = ProjectManager.get_projects(search="project_1")
        self.assertEqual(len(search_result['data']['projects']), 1)
        self.assertEqual(search_result['data']['projects'][0]['name'], "project_1")
        
        # 测试标签筛选
        tag_result = ProjectManager.get_projects(tags=["测试"])
        self.assertEqual(len(tag_result['data']['projects']), 3)  # project_1, project_3, project_5
        
        print("✓ 获取项目列表功能测试通过")
    
    def test_get_project(self):
        """测试获取项目详情功能
        
        验证获取项目详情功能是否正常工作
        """
        print("\n测试获取项目详情功能...")
        
        # 先创建一个测试项目
        create_result = ProjectManager.create_project(
            name="detail_test",
            description="项目详情测试",
            tags=["详情", "测试"]
        )
        self.assertTrue(create_result['success'])
        
        project_id = create_result['data']['id']
        
        # 获取项目详情
        detail_result = ProjectManager.get_project(project_id)
        
        # 检查结果
        self.assertTrue(detail_result['success'])
        self.assertIn('data', detail_result)
        
        # 验证项目信息
        project_data = detail_result['data']
        self.assertEqual(project_data['name'], "detail_test")
        self.assertEqual(project_data['description'], "项目详情测试")
        self.assertIn("详情", project_data['tags'])
        self.assertIn("测试", project_data['tags'])
        
        print("✓ 获取项目详情功能测试通过")
    
    def test_get_tags(self):
        """测试获取标签列表功能
        
        验证获取所有项目标签功能是否正常工作
        """
        print("\n测试获取标签列表功能...")
        
        # 先创建几个带标签的项目
        ProjectManager.create_project(
            name="tag_test_1",
            tags=["标签1", "公共标签"]
        )
        ProjectManager.create_project(
            name="tag_test_2",
            tags=["标签2", "公共标签"]
        )
        
        # 获取标签列表
        tags_result = ProjectManager.get_tags()
        
        # 检查结果
        self.assertTrue(tags_result['success'])
        self.assertIn('data', tags_result)
        
        # 验证标签数量和内容
        tags = tags_result['data']
        tag_names = [tag['name'] for tag in tags]
        self.assertEqual(len(tags), 3)  # 标签1, 标签2, 公共标签
        self.assertIn("标签1", tag_names)
        self.assertIn("标签2", tag_names)
        self.assertIn("公共标签", tag_names)
        
        print("✓ 获取标签列表功能测试通过")
    
    def test_detect_work_path(self):
        """测试自动检测工作路径功能
        
        验证自动检测工作路径功能是否正常工作
        """
        print("\n测试自动检测工作路径功能...")
        
        # 创建临时项目目录
        temp_dir = tempfile.mkdtemp()
        
        try:
            # 测试单文件情况
            with open(os.path.join(temp_dir, "main.py"), "w") as f:
                f.write("print('hello')")
            
            work_path = ProjectManager._detect_work_path(temp_dir)
            self.assertEqual(work_path, '/')
            
            # 测试子目录情况
            sub_dir = os.path.join(temp_dir, "subdir")
            os.makedirs(sub_dir, exist_ok=True)
            with open(os.path.join(sub_dir, "main.py"), "w") as f:
                f.write("print('hello from subdir')")
            
            work_path = ProjectManager._detect_work_path(temp_dir)
            self.assertEqual(work_path, '/subdir')
            
            print("✓ 自动检测工作路径功能测试通过")
        finally:
            # 清理临时目录
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    # 设置测试环境变量
    os.environ['TESTING'] = 'true'
    
    print("开始测试项目管理模块...")
    
    try:
        # 运行所有测试
        unittest.main()
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")
        sys.exit(1)
    finally:
        print("\n测试完成！")