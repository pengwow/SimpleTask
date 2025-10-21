#!/bin/bash

# Python虚拟环境管理模块启动脚本
# 用于初始化数据库并启动后端服务

# 设置脚本执行选项：遇到错误立即退出
set -e

# 定义颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # 无颜色

# 打印带颜色的消息
function print_color() {
    color=$1
    message=$2
    echo -e "${color}${message}${NC}"
}

# 打印成功消息
function print_success() {
    print_color "${GREEN}" "✓ $1"
}

# 打印错误消息
function print_error() {
    print_color "${RED}" "✗ $1"
}

# 打印警告消息
function print_warning() {
    print_color "${YELLOW}" "! $1"
}

# 打印信息消息
function print_info() {
    print_color "${BLUE}" "ℹ $1"
}

# 检查Python是否安装
function check_python() {
    print_info "检查Python安装..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | grep -o 'Python [0-9.]*')
        print_success "已检测到Python安装: $PYTHON_VERSION"
        return 0
    else
        print_error "未检测到Python安装，请先安装Python 3.6或更高版本"
        return 1
    fi
}

# 安装依赖
function install_dependencies() {
    print_info "安装项目依赖..."
    if [ -f requirements.txt ]; then
        pip3 install -r requirements.txt
        if [ $? -eq 0 ]; then
            print_success "依赖安装成功"
        else
            print_warning "依赖安装可能有部分失败，继续执行..."
        fi
    else
        print_warning "requirements.txt文件不存在，跳过依赖安装"
    fi
}

# 初始化数据库
function init_database() {
    print_info "初始化数据库..."
    python3 init_db.py
    if [ $? -eq 0 ]; then
        print_success "数据库初始化成功"
    else
        print_error "数据库初始化失败，请检查错误信息"
        return 1
    fi
}

# 启动服务
function start_server() {
    print_info "启动Python虚拟环境管理服务..."
    print_info "服务将在 http://localhost:5001 启动"
    print_info "按 Ctrl+C 停止服务"
    
    # 设置PYTHONPATH为项目根目录
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    
    # 使用python3运行主服务文件
    python3 app/app.py
    
    if [ $? -ne 0 ]; then
        print_error "服务启动失败，请检查错误信息"
        return 1
    fi
}

# 启动FastAPI服务
function start_fastapi() {
    print_info "启动FastAPI服务..."
    print_info "服务将在 http://localhost:8000 启动"
    print_info "API文档地址: http://localhost:8000/docs"
    print_info "按 Ctrl+C 停止服务"
    
    # 设置PYTHONPATH为项目根目录
    export PYTHONPATH="$(pwd):$PYTHONPATH"
    
    # 使用python3运行main.py启动FastAPI服务
    python3 main.py
    
    if [ $? -ne 0 ]; then
        print_error "FastAPI服务启动失败，请检查错误信息"
        return 1
    fi
}

# 重启服务（默认行为）
function restart_service() {
    print_info "执行服务重启操作..."
    
    # 查找并停止现有进程
    print_info "查找并停止现有服务进程..."
    
    # 查找FastAPI进程（main.py）
    fastapi_pid=$(ps aux | grep "python3 main.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$fastapi_pid" ]; then
        print_info "停止FastAPI进程: $fastapi_pid"
        kill -15 $fastapi_pid 2>/dev/null || true
        sleep 2
        # 强制终止仍在运行的进程
        kill -9 $fastapi_pid 2>/dev/null || true
    fi
    
    # 查找app进程（app.py）
    app_pid=$(ps aux | grep "python3 app/app.py" | grep -v grep | awk '{print $2}')
    if [ ! -z "$app_pid" ]; then
        print_info "停止App进程: $app_pid"
        kill -15 $app_pid 2>/dev/null || true
        sleep 2
        # 强制终止仍在运行的进程
        kill -9 $app_pid 2>/dev/null || true
    fi
    
    print_success "进程停止完成"
    print_info "正在启动服务..."
    
    # 启动FastAPI服务
    start_fastapi
}

# 清理虚拟环境
function cleanup_envs() {
    print_info "开始清理虚拟环境..."
    
    # 查找并终止与虚拟环境相关的进程
    print_info "查找并终止与虚拟环境相关的进程..."
    if [ -d "envs" ]; then
        # 获取所有虚拟环境路径
        venv_paths=$(find envs -name "bin" -type d | sed 's/\/bin$//')
        
        if [ ! -z "$venv_paths" ]; then
            for venv_path in $venv_paths; do
                # 获取虚拟环境中的Python路径
                python_path="$venv_path/bin/python"
                if [ -f "$python_path" ]; then
                    # 查找使用该Python的进程
                    pids=$(lsof -t "$python_path" 2>/dev/null || true)
                    if [ ! -z "$pids" ]; then
                        print_info "终止使用虚拟环境 $venv_path 的进程: $pids"
                        kill -15 $pids 2>/dev/null || true
                        # 等待进程结束
                        sleep 2
                        # 强制终止仍在运行的进程
                        kill -9 $pids 2>/dev/null || true
                    fi
                fi
            done
        fi
    fi
    
    # 清理虚拟环境目录
    if [ -d "envs" ]; then
        print_info "删除所有虚拟环境..."
        rm -rf envs/*
        if [ $? -eq 0 ]; then
            print_success "虚拟环境清理成功"
        else
            print_error "虚拟环境清理失败"
            return 1
        fi
    else
        print_info "envs目录不存在，跳过清理"
    fi
    
    return 0
}

# 显示帮助信息
function show_help() {
    echo "使用方法: $0 [选项]"
    echo "选项:"
    echo "  --help, -h          显示帮助信息"
    echo "  --skip-deps         跳过依赖安装"
    echo "  --skip-db           跳过数据库初始化"
    echo "  --only-db           仅初始化数据库"
    echo "  --test              运行API测试"
    echo "  --cleanup           清理所有虚拟环境"
    echo "  --start-server      启动原始服务"
    echo "  --start-fastapi     启动FastAPI服务"
    echo ""
    echo "示例:"
    echo "  $0                  默认执行重启操作（停止现有进程并启动FastAPI服务）"
    echo "  $0 --skip-deps      跳过依赖安装，直接初始化数据库并启动服务"
    echo "  $0 --skip-db        跳过数据库初始化，直接启动服务"
    echo "  $0 --only-db        仅初始化数据库"
    echo "  $0 --test           运行API测试"
    echo "  $0 --cleanup        清理所有虚拟环境和相关进程"
    echo "  $0 --start-server   启动原始服务"
    echo "  $0 --start-fastapi  启动FastAPI服务"
}

# 主函数
function main() {
    # 默认参数
    SKIP_DEPS=false
    SKIP_DB=false
    ONLY_DB=false
    RUN_TEST=false
    CLEANUP=false
    START_SERVER=false
    START_FASTAPI=false
    RESTART=true  # 默认执行重启操作
    
    # 解析命令行参数
    for arg in "$@"; do
        case $arg in
            --help|-h)
                show_help
                return 0
                ;;
            --skip-deps)
                SKIP_DEPS=true
                RESTART=false
                ;;
            --skip-db)
                SKIP_DB=true
                RESTART=false
                ;;
            --only-db)
                ONLY_DB=true
                RESTART=false
                ;;
            --test)
                RUN_TEST=true
                RESTART=false
                ;;
            --cleanup)
                CLEANUP=true
                RESTART=false
                ;;
            --start-server)
                START_SERVER=true
                RESTART=false
                ;;
            --start-fastapi)
                START_FASTAPI=true
                RESTART=false
                ;;
            *)
                print_error "未知选项: $arg"
                show_help
                return 1
                ;;
        esac
    done
    
    # 检查Python安装
    if ! check_python; then
        return 1
    fi
    
    # 如果只是清理环境
    if [ "$CLEANUP" = true ]; then
        if ! cleanup_envs; then
            print_error "清理操作失败"
            return 1
        fi
        print_success "清理操作完成"
        return 0
    fi
    
    # 如果只是运行测试
    if [ "$RUN_TEST" = true ]; then
        print_info "运行API测试..."
        python3 test_envs_api.py
        return $?
    fi
    
    # 如果只是初始化数据库
    if [ "$ONLY_DB" = true ]; then
        if ! init_database; then
            return 1
        fi
        return 0
    fi
    
    # 默认执行重启操作
    if [ "$RESTART" = true ]; then
        if ! restart_service; then
            return 1
        fi
        return 0
    fi
    
    # 安装依赖（可选）
    if [ "$SKIP_DEPS" = false ]; then
        install_dependencies
    else
        print_warning "跳过依赖安装"
    fi
    
    # 初始化数据库（可选）
    if [ "$SKIP_DB" = false ]; then
        if ! init_database; then
            return 1
        fi
    else
        print_warning "跳过数据库初始化"
    fi
    
    # 启动指定服务
    if [ "$START_SERVER" = true ]; then
        if ! start_server; then
            return 1
        fi
    elif [ "$START_FASTAPI" = true ]; then
        if ! start_fastapi; then
            return 1
        fi
    else
        # 兼容原有行为，启动原始服务
        if ! start_server; then
            return 1
        fi
    fi
    
    return 0
}

# 执行主函数并返回退出码
main "$@"
exit $?