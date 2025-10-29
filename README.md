# SimpleTask: Python虚拟环境管理工具

提供了强大而灵活的Python虚拟环境管理功能，支持多个Python版本，通过直观的Web界面，可以轻松创建、编辑和管理虚拟环境，为您的任务提供独立的运行环境。

## 功能特点

### 1. 环境复用与管理
- **一对多关系**: 一个虚拟环境可以同时服务于多个定时任务，提高资源利用效率
- **灵活配置**: 支持自定义环境名称和依赖包，满足不同任务的需求
- **版本选择**: 支持选择不同的Python版本，适应各种项目需求（默认使用Python 3.9.21）

### 2. 实时安装日志
- **详细记录**: 完整记录包安装过程，包括下载进度、依赖解析等信息
- **错误追踪**: 清晰显示安装过程中的警告和错误信息，便于问题排查
- **实时反馈**: 安装过程实时展示，无需等待即可了解安装状态

### 3. 镜像源管理
- **多源支持**: 内置多个常用PyPI镜像源
  - 官方PyPI源
  - 阿里云镜像源
  - 清华大学镜像源
  - 中国科学技术大学镜像源
  - 华为云镜像源
  - 腾讯云镜像源
- **自定义配置**: 支持添加、编辑和删除镜像源
- **灵活切换**: 可随时切换到最适合的镜像源，优化包下载速度

## 技术栈

- **后端框架**: Flask
- **数据库**: SQLite3
- **前端集成**: nicegui
- **虚拟化**: Python venv

## 安装部署

### 1. 安装依赖

```bash
cd /Users/liupeng/workspace/SimpleTask
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
python init_db.py init
```

### 3. 启动后台服务

```bash
chmod +x start.sh
./start.sh
```

服务将在 http://localhost:5001 启动

## API接口文档

### 虚拟环境管理

#### 获取所有环境列表
- **URL**: `/api/envs`
- **Method**: `GET`
- **返回**: JSON格式的环境列表

#### 获取单个环境详情
- **URL**: `/api/envs/<int:env_id>`
- **Method**: `GET`
- **返回**: JSON格式的环境详情

#### 创建新环境
- **URL**: `/api/envs`
- **Method**: `POST`
- **请求体**: 
  ```json
  {
    "name": "环境名称",
    "python_version": "3.9.21",  # 可选，默认3.9.21
    "requirements": "requests\npandas"  # 可选，依赖包列表，每行一个
  }
  ```
- **返回**: 创建结果和环境ID

#### 更新环境
- **URL**: `/api/envs/<int:env_id>`
- **Method**: `PUT`
- **请求体**: 
  ```json
  {
    "requirements": "新的依赖包列表"
  }
  ```
- **返回**: 更新结果

#### 删除环境
- **URL**: `/api/envs/<int:env_id>`
- **Method**: `DELETE`
- **返回**: 删除结果

### 日志管理

#### 获取历史日志
- **URL**: `/api/envs/<int:env_id>/logs`
- **Method**: `GET`
- **返回**: JSON格式的日志列表

#### 实时日志流
- **URL**: `/api/envs/<int:env_id>/log_stream`
- **Method**: `GET`
- **返回**: Server-Sent Events (SSE) 实时日志流

### 镜像源管理

#### 获取所有镜像源
- **URL**: `/api/mirrors`
- **Method**: `GET`
- **返回**: JSON格式的镜像源列表

#### 获取单个镜像源
- **URL**: `/api/mirrors/<int:mirror_id>`
- **Method**: `GET`
- **返回**: JSON格式的镜像源详情

#### 创建新镜像源
- **URL**: `/api/mirrors`
- **Method**: `POST`
- **请求体**: 
  ```json
  {
    "name": "镜像源名称",
    "url": "https://mirror.example.com/simple/",
    "description": "镜像源描述"  # 可选
  }
  ```
- **返回**: 创建结果和镜像源ID

#### 更新镜像源
- **URL**: `/api/mirrors/<int:mirror_id>`
- **Method**: `PUT`
- **请求体**: 
  ```json
  {
    "name": "新名称",  # 可选
    "url": "新地址",  # 可选
    "description": "新描述",  # 可选
    "is_active": true  # 可选，设为活跃镜像源
  }
  ```
- **返回**: 更新结果

#### 删除镜像源
- **URL**: `/api/mirrors/<int:mirror_id>`
- **Method**: `DELETE`
- **返回**: 删除结果

#### 获取活跃镜像源
- **URL**: `/api/mirrors/active`
- **Method**: `GET`
- **返回**: 当前活跃的镜像源信息

## 目录结构

```
SimpleTask/
├── app/                  # 主应用目录
│   ├── api/              # API接口实现
│   ├── dashboard/        # 仪表盘模块
│   ├── models/           # 数据模型
│   ├── utils/            # 工具函数
│   ├── virtual_envs/     # 虚拟环境管理
│   ├── logs/             # 日志模块
│   ├── projects/         # 项目管理
│   ├── notifications/    # 通知模块
│   ├── settings/         # 系统设置
│   ├── tasks/            # 任务管理
│   ├── python_versions/  # Python版本管理
│   └── app.py            # 应用入口
├── init_db.py            # 数据库初始化脚本
├── start.sh              # 启动脚本
├── requirements.txt      # 项目依赖
└── simpletask.db        # SQLite数据库文件
```

## 注意事项

1. 确保您的系统安装了多个Python版本，以支持不同版本的虚拟环境创建
2. 虚拟环境创建和依赖包安装过程可能需要较长时间，请耐心等待
3. 实时日志流使用Server-Sent Events技术，确保您的前端能够正确处理
4. 数据库默认存储在项目根目录，可根据需要修改配置
5. 如需重置数据库，请使用 `python init_db.py drop` 命令（谨慎使用，将删除所有数据）

## 开发说明

如需扩展功能或修改代码，请参考以下文件：

- **app/app.py**: 应用主入口
- **app/api/routes.py**: API接口定义
- **app/db/models.py**: 数据模型定义
- **app/virtual_envs/env_manager.py**: 虚拟环境管理逻辑
- **app/utils/tools.py**: 工具函数
- **init_db.py**: 数据库初始化和管理工具

## License

MIT License