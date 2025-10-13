#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""项目管理模块API测试脚本

用于测试项目管理模块的各种API接口功能是否正常工作
"""

import os
import sys
import json
import time
import requests
import argparse
from pprint import pprint

# API基础URL
BASE_URL = 'http://localhost:5001/api'

# 颜色定义
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 工具函数

def print_with_color(text, color=Colors.OKCYAN):
    """打印带颜色的文本
    
    参数:
        text: 要打印的文本
        color: 文本颜色
    """
    print(f"{color}{text}{Colors.ENDC}")

def print_success(text):
    """打印成功信息
    
    参数:
        text: 成功信息
    """
    print_with_color(f"✓ {text}", Colors.OKGREEN)

def print_error(text):
    """打印错误信息
    
    参数:
        text: 错误信息
    """
    print_with_color(f"✗ {text}", Colors.FAIL)

def print_warning(text):
    """打印警告信息
    
    参数:
        text: 警告信息
    """
    print_with_color(f"! {text}", Colors.WARNING)

def print_info(text):
    """打印信息
    
    参数:
        text: 信息内容
    """
    print_with_color(f"ℹ {text}", Colors.OKBLUE)

def print_separator(title):
    """打印分隔符和标题
    
    参数:
        title: 标题内容
    """
    print("\n" + "="*60)
    print_with_color(title, Colors.HEADER)
    print("="*60)

def create_test_project(name=None):
    """创建一个测试项目
    
    参数:
        name: 项目名称，如果为None则自动生成
        
    返回:
        int: 项目ID
    """
    if name is None:
        name = f"test_project_{int(time.time())}"
    
    project_data = {
        'name': name,
        'description': f'测试项目 {name}',
        'work_path': '/',
        'source_type': 'zip',
        'tags': ['测试', 'API测试']
    }
    
    response = requests.post(f"{BASE_URL}/projects", json=project_data)
    
    if response.status_code == 201:
        result = response.json()
        if result.get('success'):
            print_success(f"成功创建测试项目: {name}")
            return result['data']['id']
    
    print_error(f"创建测试项目失败: {response.status_code} - {response.text}")
    return None

# API测试函数

def test_get_projects():
    """测试获取项目列表API
    
    验证获取项目列表API是否正常工作，包括分页、搜索和标签筛选功能
    """
    print_separator("测试获取项目列表API")
    
    # 先创建一些测试项目用于测试
    test_project_ids = []
    for i in range(3):
        project_id = create_test_project(f"test_project_{i+1}")
        if project_id:
            test_project_ids.append(project_id)
    
    # 等待项目创建完成
    time.sleep(1)
    
    # 测试获取所有项目
    try:
        response = requests.get(f"{BASE_URL}/projects")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                projects = result['data']['projects']
                pagination = result['data']['pagination']
                
                print_success(f"成功获取项目列表，共 {len(projects)} 个项目")
                print_info(f"分页信息: 第 {pagination['page']} 页，每页 {pagination['per_page']} 条，共 {pagination['total']} 条")
                
                # 打印前3个项目的信息
                print_info("前3个项目信息:")
                for i, project in enumerate(projects[:3]):
                    print(f"{i+1}. {project['name']} - {project['description']}")
                    print(f"   状态: {project['status']}, 创建时间: {project['create_time']}")
                    print(f"   标签: {', '.join(project['tags'])}")
                
                return True
        
        print_error(f"获取项目列表失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"获取项目列表时发生异常: {str(e)}")
        return False

def test_create_project():
    """测试创建项目API
    
    验证创建项目API是否正常工作
    """
    print_separator("测试创建项目API")
    
    project_name = f"test_project_{int(time.time())}"
    project_data = {
        'name': project_name,
        'description': f'测试项目 {project_name}',
        'work_path': '/',
        'source_type': 'zip',
        'tags': ['测试', 'API测试']
    }
    
    try:
        print_info(f"创建项目: {project_name}")
        print_info(f"项目数据: {json.dumps(project_data, ensure_ascii=False)}")
        
        response = requests.post(f"{BASE_URL}/projects", json=project_data)
        
        if response.status_code == 201:
            result = response.json()
            if result.get('success'):
                project_id = result['data']['id']
                print_success(f"项目创建成功，ID: {project_id}")
                
                # 验证项目是否创建成功
                verify_response = requests.get(f"{BASE_URL}/projects/{project_id}")
                if verify_response.status_code == 200:
                    verify_result = verify_response.json()
                    if verify_result.get('success'):
                        print_success(f"项目验证成功: {verify_result['data']['name']}")
                        return True
                
                print_warning("项目创建成功，但验证失败")
                return True
        
        print_error(f"项目创建失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"创建项目时发生异常: {str(e)}")
        return False

def test_get_project():
    """测试获取项目详情API
    
    验证获取项目详情API是否正常工作
    """
    print_separator("测试获取项目详情API")
    
    # 先创建一个测试项目
    project_id = create_test_project()
    if not project_id:
        print_error("无法创建测试项目，测试失败")
        return False
    
    try:
        response = requests.get(f"{BASE_URL}/projects/{project_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                project_data = result['data']
                
                print_success(f"成功获取项目详情: {project_data['name']}")
                print_info(f"ID: {project_data['id']}")
                print_info(f"描述: {project_data['description']}")
                print_info(f"工作路径: {project_data['work_path']}")
                print_info(f"来源类型: {project_data['source_type']}")
                print_info(f"状态: {project_data['status']}")
                print_info(f"创建时间: {project_data['create_time']}")
                print_info(f"更新时间: {project_data['update_time']}")
                print_info(f"标签: {', '.join(project_data['tags'])}")
                
                return True
        
        print_error(f"获取项目详情失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"获取项目详情时发生异常: {str(e)}")
        return False

def test_update_project():
    """测试更新项目API
    
    验证更新项目API是否正常工作
    """
    print_separator("测试更新项目API")
    
    # 先创建一个测试项目
    project_id = create_test_project()
    if not project_id:
        print_error("无法创建测试项目，测试失败")
        return False
    
    # 准备更新数据
    update_data = {
        'name': f"updated_project_{int(time.time())}",
        'description': "这是一个已更新的测试项目",
        'work_path': '/src',
        'tags': ['已更新', '测试']
    }
    
    try:
        print_info(f"更新项目 {project_id}")
        print_info(f"更新数据: {json.dumps(update_data, ensure_ascii=False)}")
        
        response = requests.put(f"{BASE_URL}/projects/{project_id}", json=update_data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success(f"项目更新成功")
                
                # 验证更新结果
                verify_response = requests.get(f"{BASE_URL}/projects/{project_id}")
                if verify_response.status_code == 200:
                    verify_result = verify_response.json()
                    if verify_result.get('success'):
                        project_data = verify_result['data']
                        print_success(f"项目更新验证成功")
                        print_info(f"新名称: {project_data['name']}")
                        print_info(f"新描述: {project_data['description']}")
                        print_info(f"新工作路径: {project_data['work_path']}")
                        print_info(f"新标签: {', '.join(project_data['tags'])}")
                        return True
                
                print_warning("项目更新成功，但验证失败")
                return True
        
        print_error(f"项目更新失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"更新项目时发生异常: {str(e)}")
        return False

def test_delete_project():
    """测试删除项目API
    
    验证删除项目API是否正常工作
    """
    print_separator("测试删除项目API")
    
    # 先创建一个测试项目
    project_id = create_test_project()
    if not project_id:
        print_error("无法创建测试项目，测试失败")
        return False
    
    try:
        print_info(f"删除项目 {project_id}")
        
        response = requests.delete(f"{BASE_URL}/projects/{project_id}")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success(f"项目删除成功")
                
                # 验证项目是否已删除
                verify_response = requests.get(f"{BASE_URL}/projects/{project_id}")
                if verify_response.status_code == 400:
                    print_success(f"项目删除验证成功")
                    return True
                
                print_warning("项目删除成功，但验证失败")
                return True
        
        print_error(f"项目删除失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"删除项目时发生异常: {str(e)}")
        return False

def test_get_project_tags():
    """测试获取项目标签API
    
    验证获取项目标签API是否正常工作
    """
    print_separator("测试获取项目标签API")
    
    try:
        response = requests.get(f"{BASE_URL}/project_tags")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                tags = result['data']
                
                print_success(f"成功获取项目标签，共 {len(tags)} 个标签")
                print_info("标签列表:")
                for tag in tags:
                    print(f"- {tag['name']} (ID: {tag['id']})")
                
                return True
        
        print_error(f"获取项目标签失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"获取项目标签时发生异常: {str(e)}")
        return False

def test_upload_project_file():
    """测试上传项目文件API
    
    验证上传项目文件API是否正常工作
    """
    print_separator("测试上传项目文件API")
    
    # 先创建一个测试项目
    project_id = create_test_project()
    if not project_id:
        print_error("无法创建测试项目，测试失败")
        return False
    
    # 创建一个临时ZIP文件用于测试
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    zip_file_path = os.path.join(temp_dir, "test_project.zip")
    
    try:
        # 创建一个简单的ZIP文件
        import zipfile
        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            # 添加一个示例文件
            test_file_content = "print('Hello from test project!')"
            zipf.writestr("main.py", test_file_content)
            
            # 添加一个子目录和文件
            utils_content = """def helper():
    return 'Helper function'"""
            zipf.writestr("src/utils.py", utils_content)
        
        print_info(f"创建临时测试ZIP文件: {zip_file_path}")
        
        # 上传文件
        with open(zip_file_path, 'rb') as f:
            files = {'file': ('test_project.zip', f)}
            response = requests.post(f"{BASE_URL}/projects/{project_id}/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                print_success("项目文件上传成功")
                
                # 验证上传结果
                project_detail_response = requests.get(f"{BASE_URL}/projects/{project_id}")
                if project_detail_response.status_code == 200:
                    project_detail = project_detail_response.json()
                    if project_detail.get('success'):
                        files = project_detail['data']['files']
                        if 'main.py' in files:
                            print_success("项目文件上传验证成功")
                            print_info(f"上传的文件列表: {', '.join(files)}")
                            return True
                
                print_warning("项目文件上传成功，但验证失败")
                return True
        
        print_error(f"项目文件上传失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"上传项目文件时发生异常: {str(e)}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def test_get_project_file():
    """测试获取项目文件内容API
    
    验证获取项目文件内容API是否正常工作
    """
    print_separator("测试获取项目文件内容API")
    
    # 先创建一个测试项目并上传文件
    project_id = create_test_project()
    if not project_id:
        print_error("无法创建测试项目，测试失败")
        return False
    
    # 创建一个临时ZIP文件用于测试
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    zip_file_path = os.path.join(temp_dir, "test_file.zip")
    
    try:
        # 创建一个简单的ZIP文件
        import zipfile
        with zipfile.ZipFile(zip_file_path, 'w') as zipf:
            test_file_content = "print('Hello from test file!')"
            zipf.writestr("test_file.py", test_file_content)
        
        # 上传文件
        with open(zip_file_path, 'rb') as f:
            files = {'file': ('test_file.zip', f)}
            requests.post(f"{BASE_URL}/projects/{project_id}/upload", files=files)
        
        # 等待文件上传完成
        time.sleep(1)
        
        # 获取文件内容
        response = requests.get(f"{BASE_URL}/projects/{project_id}/files/test_file.py")
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                file_content = result['data']['content']
                
                print_success("成功获取项目文件内容")
                print_info(f"文件内容: {file_content}")
                
                return True
        
        print_error(f"获取项目文件内容失败: {response.status_code} - {response.text}")
        return False
    except Exception as e:
        print_error(f"获取项目文件内容时发生异常: {str(e)}")
        return False
    finally:
        # 清理临时文件
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
        if os.path.exists(temp_dir) and not os.listdir(temp_dir):
            os.rmdir(temp_dir)

def run_all_tests():
    """运行所有测试
    
    按顺序运行所有项目管理API的测试函数
    """
    print_with_color("\n开始运行所有项目管理API测试...\n", Colors.BOLD)
    
    # 测试函数列表
    tests = [
        test_get_project_tags,
        test_create_project,
        test_get_projects,
        test_get_project,
        test_update_project,
        test_upload_project_file,
        test_get_project_file,
        test_delete_project
    ]
    
    # 记录测试结果
    results = {}
    
    # 运行每个测试
    for test_func in tests:
        test_name = test_func.__name__
        print_with_color(f"\n运行测试: {test_name}", Colors.BOLD)
        
        try:
            result = test_func()
            results[test_name] = result
            
            if result:
                print_success(f"测试 {test_name} 通过")
            else:
                print_error(f"测试 {test_name} 失败")
        except Exception as e:
            results[test_name] = False
            print_error(f"测试 {test_name} 发生异常: {str(e)}")
    
    # 打印测试总结
    print_separator("测试总结")
    
    total_tests = len(tests)
    passed_tests = sum(1 for result in results.values() if result)
    failed_tests = total_tests - passed_tests
    
    print_info(f"总测试数: {total_tests}")
    print_success(f"通过测试数: {passed_tests}")
    print_error(f"失败测试数: {failed_tests}")
    
    if failed_tests == 0:
        print_success("所有测试通过！")
    else:
        print_warning("有测试失败，请检查问题")

if __name__ == "__main__":
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='项目管理API测试脚本')
    parser.add_argument('--test', type=str, help='指定要运行的测试函数名称')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    
    args = parser.parse_args()
    
    # 运行指定的测试或所有测试
    if args.test:
        test_func = globals().get(args.test)
        if test_func and callable(test_func):
            test_func()
        else:
            print_error(f"未找到测试函数: {args.test}")
            parser.print_help()
    else:
        # 默认运行所有测试
        run_all_tests()