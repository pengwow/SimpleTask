#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试脚本：验证API接口功能

用于测试Python虚拟环境管理工具的主要API功能是否正常工作。
"""

import requests
import time
import json
import sys
from datetime import datetime

BASE_URL = "http://localhost:5001/api"


def print_separator(title):
    """打印分隔符和标题"""
    print("\n" + "="*60)
    print(f"{title}")
    print("="*60)


def test_get_mirrors():
    """测试获取镜像源列表"""
    print_separator("测试获取镜像源列表")
    try:
        response = requests.get(f"{BASE_URL}/mirrors")
        if response.status_code == 200:
            mirrors = response.json()
            print(f"成功获取 {len(mirrors)} 个镜像源")
            for mirror in mirrors:
                status = "活跃" if mirror.get('is_active') else "非活跃"
                print(f"- {mirror['name']} ({status}): {mirror['url']}")
            return True
        else:
            print(f"获取镜像源失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"获取镜像源时发生错误: {str(e)}")
        return False


def test_get_active_mirror():
    """测试获取活跃镜像源"""
    print_separator("测试获取活跃镜像源")
    try:
        response = requests.get(f"{BASE_URL}/mirrors/active")
        if response.status_code == 200:
            mirror = response.json()
            print(f"成功获取活跃镜像源: {mirror['name']} - {mirror['url']}")
            return True
        else:
            print(f"获取活跃镜像源失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"获取活跃镜像源时发生错误: {str(e)}")
        return False


def test_get_envs():
    """测试获取虚拟环境列表"""
    print_separator("测试获取虚拟环境列表")
    try:
        response = requests.get(f"{BASE_URL}/envs")
        if response.status_code == 200:
            envs = response.json()
            print(f"成功获取 {len(envs)} 个虚拟环境")
            for env in envs:
                status = "活跃" if env.get('is_active') else "非活跃"
                print(f"- {env['name']} (ID: {env['id']}, {status})")
            return True
        else:
            print(f"获取虚拟环境失败: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"获取虚拟环境时发生错误: {str(e)}")
        return False


def test_create_env():
    """测试创建虚拟环境"""
    print_separator("测试创建虚拟环境")
    try:
        test_env_name = f"test-env-{int(time.time())}"
        print(f"创建测试环境: {test_env_name}")
        
        payload = {
            "name": test_env_name,
            "python_version": "3.9",
            "requirements": "requests\npytest"
        }
        
        response = requests.post(f"{BASE_URL}/envs", json=payload)
        
        if response.status_code == 201:
            result = response.json()
            env_id = result.get('env_id')
            print(f"成功创建虚拟环境，ID: {env_id}")
            return True, env_id
        else:
            print(f"创建虚拟环境失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text}")
            return False, None
    except Exception as e:
        print(f"创建虚拟环境时发生错误: {str(e)}")
        return False, None


def test_delete_env(env_id):
    """测试删除虚拟环境"""
    print_separator(f"测试删除虚拟环境 (ID: {env_id})")
    try:
        response = requests.delete(f"{BASE_URL}/envs/{env_id}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"成功删除虚拟环境")
            return True
        else:
            print(f"删除虚拟环境失败: HTTP {response.status_code}")
            print(f"错误信息: {response.text}")
            return False
    except Exception as e:
        print(f"删除虚拟环境时发生错误: {str(e)}")
        return False


def main():
    """主函数，运行所有测试"""
    print("=== Python虚拟环境管理工具 API测试 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试API地址: {BASE_URL}")
    
    results = {
        "镜像源列表": test_get_mirrors(),
        "活跃镜像源": test_get_active_mirror(),
        "虚拟环境列表": test_get_envs(),
    }
    
    # 测试创建和删除环境
    create_success, env_id = test_create_env()
    results["创建虚拟环境"] = create_success
    
    if create_success and env_id:
        # 重新获取环境列表，确认创建成功
        test_get_envs()
        
        # 测试删除环境
        delete_success = test_delete_env(env_id)
        results["删除虚拟环境"] = delete_success
        
        # 重新获取环境列表，确认删除成功
        test_get_envs()
    
    # 打印测试结果摘要
    print_separator("测试结果摘要")
    success_count = sum(1 for result in results.values() if result)
    total_count = len(results)
    
    print(f"测试总数: {total_count}")
    print(f"成功数: {success_count}")
    print(f"失败数: {total_count - success_count}")
    
    print("\n详细结果:")
    for test_name, success in results.items():
        status = "✓ 成功" if success else "✗ 失败"
        print(f"- {test_name}: {status}")
    
    if success_count == total_count:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print("\n⚠️ 部分测试失败，请检查应用是否正常运行。")
        print("提示: 确保服务已启动，运行 './start.sh' 启动服务。")
        return 1


if __name__ == "__main__":
    sys.exit(main())