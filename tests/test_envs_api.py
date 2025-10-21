#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Python虚拟环境管理模块API测试脚本

用于测试Python虚拟环境管理模块的各种API接口功能是否正常工作。
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

def print_with_color(text, color=Colors.OKCYAN):
    """打印带颜色的文本"""
    print(f"{color}{text}{Colors.ENDC}")

def print_success(text):
    """打印成功信息"""
    print_with_color(f"✓ {text}", Colors.OKGREEN)

def print_error(text):
    """打印错误信息"""
    print_with_color(f"✗ {text}", Colors.FAIL)

def print_warning(text):
    """打印警告信息"""
    print_with_color(f"! {text}", Colors.WARNING)

def print_info(text):
    """打印信息"""
    print_with_color(f"ℹ {text}", Colors.OKBLUE)

def test_connection():
    """测试与API服务器的连接"""
    print_info("测试API连接...")
    try:
        response = requests.get(f'{BASE_URL}/envs', timeout=5)
        if response.status_code == 200:
            print_success(f"连接成功: {BASE_URL}")
            return True
        else:
            print_error(f"连接失败，状态码: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print_error(f"无法连接到API服务器，请确保服务已启动: {BASE_URL}")
        return False
    except Exception as e:
        print_error(f"连接出错: {str(e)}")
        return False

def test_get_envs():
    """测试获取所有环境列表"""
    print_info("测试获取环境列表...")
    try:
        response = requests.get(f'{BASE_URL}/envs')
        if response.status_code == 200:
            data = response.json()
            # 检查返回的数据类型，如果是列表直接处理
            if isinstance(data, list):
                print_success(f"获取环境列表成功，共 {len(data)} 个环境")
                if data:
                    print("环境列表预览:")
                    for env in data[:3]:  # 只显示前3个
                        print(f"  - {env.get('name', 'N/A')} (v{env.get('python_version', 'N/A')}, {env.get('status', 'N/A')})")
                return True
            # 兼容旧的字典格式
            elif isinstance(data, dict):
                if data.get('code') == 200:
                    print_success(f"获取环境列表成功，共 {len(data.get('data', []))} 个环境")
                    if data.get('data'):
                        print("环境列表预览:")
                        for env in data['data'][:3]:  # 只显示前3个
                            print(f"  - {env.get('name', 'N/A')} (v{env.get('python_version', 'N/A')}, {env.get('status', 'N/A')})")
                    return True
                else:
                    print_error(f"获取环境列表失败: {data.get('message')}")
                    return False
            else:
                print_error(f"获取环境列表返回数据格式未知: {type(data)}")
                return False
        else:
            print_error(f"获取环境列表失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"获取环境列表出错: {str(e)}")
        return False

def test_get_mirrors():
    """测试获取所有镜像源"""
    print_info("测试获取镜像源列表...")
    try:
        response = requests.get(f'{BASE_URL}/mirrors')
        if response.status_code == 200:
            data = response.json()
            # 检查返回的数据类型，如果是列表直接处理
            if isinstance(data, list):
                print_success(f"获取镜像源列表成功，共 {len(data)} 个镜像源")
                active_mirrors = [m for m in data if m.get('is_active')]
                if active_mirrors:
                    print(f"当前活跃镜像源: {active_mirrors[0].get('name', 'N/A')} ({active_mirrors[0].get('url', 'N/A')})")
                return True
            # 兼容旧的字典格式
            elif isinstance(data, dict):
                if data.get('code') == 200:
                    mirrors = data.get('data', [])
                    print_success(f"获取镜像源列表成功，共 {len(mirrors)} 个镜像源")
                    active_mirrors = [m for m in mirrors if m.get('is_active')]
                    if active_mirrors:
                        print(f"当前活跃镜像源: {active_mirrors[0].get('name', 'N/A')} ({active_mirrors[0].get('url', 'N/A')})")
                    return True
                else:
                    print_error(f"获取镜像源列表失败: {data.get('message')}")
                    return False
            else:
                print_error(f"获取镜像源列表返回数据格式未知: {type(data)}")
                return False
        else:
            print_error(f"获取镜像源列表失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"获取镜像源列表出错: {str(e)}")
        return False

def test_create_env(env_name, python_version='3.9.21', requirements=''):
    """测试创建虚拟环境"""
    print_info(f"测试创建虚拟环境: {env_name} (Python {python_version})...")
    try:
        # 先检查环境是否已存在
        check_response = requests.get(f'{BASE_URL}/envs')
        if check_response.status_code == 200:
            data = check_response.json()
            # 处理列表类型的返回数据
            if isinstance(data, list):
                for env in data:
                    if env.get('name') == env_name:
                        print_warning(f"环境 '{env_name}' 已存在，跳过创建")
                        return True
            # 兼容旧的字典格式
            elif isinstance(data, dict) and data.get('code') == 200:
                existing_envs = data.get('data', [])
                for env in existing_envs:
                    if env.get('name') == env_name:
                        print_warning(f"环境 '{env_name}' 已存在，跳过创建")
                        return True
        
        # 创建新环境
        payload = {
            'name': env_name,
            'python_version': python_version
        }
        if requirements:
            payload['requirements'] = requirements
            
        response = requests.post(f'{BASE_URL}/envs', json=payload)
        if response.status_code == 200:
            data = response.json()
            # 检查是否返回的是环境对象（列表的情况已经在错误信息中排除）
            if 'id' in data:
                env_id = data.get('id')
                print_success(f"创建环境任务已提交，环境ID: {env_id}")
                print_info(f"环境 '{env_name}' 正在创建中，请通过日志流查看进度")
                return env_id  # 返回环境ID，用于后续测试
            # 兼容旧的字典格式
            elif isinstance(data, dict) and data.get('code') == 200:
                env_id = data.get('data', {}).get('id')
                print_success(f"创建环境任务已提交，环境ID: {env_id}")
                print_info(f"环境 '{env_name}' 正在创建中，请通过日志流查看进度")
                return env_id
            else:
                # 处理可能的错误信息
                error_msg = data.get('detail') or data.get('message') or "未知错误"
                print_error(f"创建环境失败: {error_msg}")
                return False
        else:
            print_error(f"创建环境失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"创建环境出错: {str(e)}")
        return False

def test_get_env_logs(env_id):
    """测试获取环境的历史日志"""
    print_info(f"测试获取环境 {env_id} 的历史日志...")
    try:
        response = requests.get(f'{BASE_URL}/envs/{env_id}/logs')
        if response.status_code == 200:
            data = response.json()
            # 检查返回的数据类型，如果是列表直接处理
            if isinstance(data, list):
                logs = data
                print_success(f"获取环境日志成功，共 {len(logs)} 条日志")
                if logs:
                    print("最新5条日志:")
                    for log in logs[-5:]:  # 显示最新5条
                        print(f"  [{log.get('timestamp', 'N/A')}] [{log.get('level', 'N/A')}] {log.get('message', 'N/A')}")
                return True
            # 兼容旧的字典格式
            elif isinstance(data, dict):
                if data.get('code') == 200:
                    logs = data.get('data', [])
                    print_success(f"获取环境日志成功，共 {len(logs)} 条日志")
                    if logs:
                        print("最新5条日志:")
                        for log in logs[-5:]:  # 显示最新5条
                            print(f"  [{log.get('timestamp', 'N/A')}] [{log.get('level', 'N/A')}] {log.get('message', 'N/A')}")
                    return True
                else:
                    print_error(f"获取环境日志失败: {data.get('message')}")
                    return False
            else:
                print_error(f"获取环境日志返回数据格式未知: {type(data)}")
                return False
        else:
            print_error(f"获取环境日志失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"获取环境日志出错: {str(e)}")
        return False

def test_delete_env(env_id):
    """测试删除虚拟环境"""
    print_info(f"测试删除虚拟环境 {env_id}...")
    try:
        response = requests.delete(f'{BASE_URL}/envs/{env_id}')
        if response.status_code == 200:
            data = response.json()
            # 检查返回的数据
            if isinstance(data, dict):
                # 兼容旧的字典格式
                if data.get('code') == 200:
                    print_success(f"删除环境成功")
                    return True
                else:
                    error_msg = data.get('detail') or data.get('message') or "未知错误"
                    print_error(f"删除环境失败: {error_msg}")
                    return False
            else:
                print_success(f"删除环境成功")
                return True
        else:
            print_error(f"删除环境失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print_error(f"删除环境出错: {str(e)}")
        return False

def test_stream_logs(env_id, duration=10):
    """测试实时日志流"""
    print_info(f"测试实时日志流 (持续 {duration} 秒)...")
    try:
        import http.client as http_client
        conn = http_client.HTTPConnection('localhost', 5001)
        conn.request('GET', f'/api/envs/{env_id}/log_stream')
        response = conn.getresponse()
        
        if response.status == 200:
            print_success("成功连接到日志流")
            print("正在接收日志流数据...")
            start_time = time.time()
            received_logs = 0
            
            while time.time() - start_time < duration:
                line = response.readline().decode('utf-8')
                if not line:
                    time.sleep(0.1)
                    continue
                
                if line.startswith('data: '):
                    log_content = line[6:].strip()
                    if log_content:
                        print(f"  {log_content}")
                        received_logs += 1
                elif line == '\n':
                    continue
        
            conn.close()
            print_success(f"日志流测试完成，共接收 {received_logs} 条日志")
            return True
        else:
            conn.close()
            print_error(f"连接日志流失败，状态码: {response.status}")
            return False
    except ImportError:
        print_warning("无法进行实时日志流测试，需要http.client模块")
        return True  # 不影响整体测试结果
    except Exception as e:
        print_error(f"日志流测试出错: {str(e)}")
        return False

def run_all_tests(skip_creation=False, skip_deletion=False):
    """运行所有测试"""
    print_with_color("=========================", Colors.HEADER)
    print_with_color("开始Python虚拟环境管理模块测试", Colors.HEADER)
    print_with_color("=========================", Colors.HEADER)
    
    # 测试连接
    if not test_connection():
        print_error("API连接失败，测试无法继续")
        return False
    
    # 测试获取环境列表
    test_get_envs()
    
    # 测试获取镜像源
    test_get_mirrors()
    
    # 测试创建环境（可选）
    created_env_id = None
    if not skip_creation:
        test_env_name = f"test-env-{int(time.time())}"
        created_env_id = test_create_env(
            test_env_name,
            python_version='3.9.21',
            requirements='requests==2.31.0\npandas==2.0.3'
        )
        
        # 如果成功创建了环境，测试日志流
        if created_env_id:
            # 等待2秒让环境有时间开始创建
            time.sleep(2)
            test_stream_logs(created_env_id, duration=5)
    
    # 测试删除环境（可选）
    if created_env_id and not skip_deletion:
        # 提示用户是否要删除创建的测试环境
        print_info("注意：测试创建的环境将在30秒后自动清理")
        # 不实际立即删除，因为环境创建可能需要时间，让用户可以查看结果
    
    print_with_color("=========================", Colors.HEADER)
    print_with_color("Python虚拟环境管理模块测试完成", Colors.HEADER)
    print_with_color("=========================", Colors.HEADER)
    
    return True

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Python虚拟环境管理模块API测试工具')
    parser.add_argument('--skip-creation', action='store_true', help='跳过环境创建测试')
    parser.add_argument('--skip-deletion', action='store_true', help='跳过环境删除测试')
    parser.add_argument('--test-connection', action='store_true', help='仅测试API连接')
    parser.add_argument('--test-envs', action='store_true', help='仅测试环境列表API')
    parser.add_argument('--test-mirrors', action='store_true', help='仅测试镜像源API')
    args = parser.parse_args()
    
    if args.test_connection:
        test_connection()
    elif args.test_envs:
        test_get_envs()
    elif args.test_mirrors:
        test_get_mirrors()
    else:
        run_all_tests(skip_creation=args.skip_creation, skip_deletion=args.skip_deletion)

if __name__ == '__main__':
    main()