#!/usr/bin/env python3
"""使用TestClient的完整测试代码

使用FastAPI的TestClient来测试API，不需要启动服务器
"""

import json
import pytest
from fastapi.testclient import TestClient
from main import app

# 创建TestClient实例
client = TestClient(app)


def test_root():
    """测试根路径"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Python虚拟环境管理系统API",
        "version": "1.0.0",
        "docs": "/docs"
    }


def test_get_mirrors():
    """测试获取镜像源列表"""
    response = client.get("/api/mirrors")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_active_mirror():
    """测试获取活跃镜像源"""
    response = client.get("/api/mirrors/active")
    print(f"Response status: {response.status_code}")
    print(f"Response content: {response.json()}")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "name" in response.json()
    assert "url" in response.json()


def test_get_envs():
    """测试获取虚拟环境列表"""
    response = client.get("/api/envs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_env():
    """测试创建虚拟环境"""
    # 准备测试数据
    env_data = {
        "name": "test-env",
        "python_version": "3.9.21",
        "requirements": "requests\npandas"
    }
    
    # 发送请求
    response = client.post("/api/envs", json=env_data)
    
    # 检查响应
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["name"] == "test-env"
    assert response.json()["python_version"] == "3.9.21"
    
    # 保存环境ID用于后续测试
    env_id = response.json()["id"]
    
    # 测试获取单个环境
    response = client.get(f"/api/envs/{env_id}")
    assert response.status_code == 200
    assert response.json()["id"] == env_id
    
    # 测试删除环境
    response = client.delete(f"/api/envs/{env_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "环境删除成功"


def test_get_python_versions():
    """测试获取Python版本列表"""
    response = client.get("/api/python_versions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_projects():
    """测试获取项目列表"""
    response = client.get("/api/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_project():
    """测试创建项目"""
    # 准备测试数据
    project_data = {
        "name": "test-project",
        "description": "测试项目",
        "work_path": "/",
        "source_type": "git",
        "source_url": "https://github.com/test/test.git",
        "branch": "main",
        "tags": ["测试", "开发"]
    }
    
    # 发送请求
    response = client.post("/api/projects", json=project_data)
    
    # 检查响应
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["name"] == "test-project"
    
    # 保存项目ID用于后续测试
    project_id = response.json()["id"]
    
    # 测试获取单个项目
    response = client.get(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id
    
    # 测试更新项目
    update_data = {
        "description": "更新后的测试项目",
        "tags": ["测试", "更新"]
    }
    response = client.put(f"/api/projects/{project_id}", json=update_data)
    assert response.status_code == 200
    assert response.json()["description"] == "更新后的测试项目"
    
    # 测试删除项目
    response = client.delete(f"/api/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["message"] == "项目删除成功"


def test_get_tasks():
    """测试获取任务列表"""
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "data" in response.json()
    assert isinstance(response.json()["data"], list)


def test_create_task():
    """测试创建任务"""
    import uuid
    # 生成唯一标识符，避免名称冲突
    unique_id = str(uuid.uuid4())[:8]
    
    # 首先创建一个虚拟环境
    env_data = {
        "name": f"test-env-for-task-{unique_id}",
        "python_version": "3.9.21"
    }
    env_response = client.post("/api/envs", json=env_data)
    print(f"Env creation response: {env_response.status_code} - {env_response.json()}")
    assert env_response.status_code == 200
    env_id = env_response.json()["id"]
    
    # 创建一个项目
    project_data = {
        "name": f"test-project-for-task-{unique_id}",
        "description": "测试项目",
        "work_path": "/"
    }
    project_response = client.post("/api/projects", json=project_data)
    print(f"Project creation response: {project_response.status_code} - {project_response.json()}")
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]
    
    # 准备任务数据
    task_data = {
        "name": f"test-task-{unique_id}",
        "description": "测试任务",
        "project_id": project_id,
        "python_env_id": env_id,
        "command": "echo 'Hello World'",
        "schedule_type": "immediate",
        "schedule_config": "{}",
        "max_instances": 1
    }
    
    # 发送请求
    response = client.post("/api/tasks", json=task_data)
    print(f"Task creation response: {response.status_code} - {response.json()}")
    
    # 检查响应
    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert response.json()["name"] == task_data["name"]
    
    # 保存任务ID用于后续测试
    task_id = response.json()["id"]
    
    # 测试获取单个任务
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["id"] == task_id
    
    # 测试删除任务
    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["success"] == True
    
    # 清理资源
    client.delete(f"/api/projects/{project_id}")
    client.delete(f"/api/envs/{env_id}")
