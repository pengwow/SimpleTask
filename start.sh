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

# 显示帮助信息
function show_help() {
    echo "使用方法: $0 [选项]"
    echo "选项:"
    echo "  --help, -h          显示帮助信息"
    echo "  --skip-deps         跳过依赖安装"
    echo "  --skip-db           跳过数据库初始化"
    echo "  --only-db           仅初始化数据库"
    echo "  --test              运行API测试"
    echo ""
    echo "示例:"
    echo "  $0                  完整启动流程（安装依赖、初始化数据库、启动服务）"
    echo "  $0 --skip-deps      跳过依赖安装，直接初始化数据库并启动服务"
    echo "  $0 --skip-db        跳过数据库初始化，直接启动服务"
    echo "  $0 --only-db        仅初始化数据库"
    echo "  $0 --test           运行API测试"
}

# 主函数
function main() {
    # 默认参数
    SKIP_DEPS=false
    SKIP_DB=false
    ONLY_DB=false
    RUN_TEST=false
    
    # 解析命令行参数
    for arg in "$@"; do
        case $arg in
            --help|-h)
                show_help
                return 0
                ;;
            --skip-deps)
                SKIP_DEPS=true
                ;;
            --skip-db)
                SKIP_DB=true
                ;;
            --only-db)
                ONLY_DB=true
                ;;
            --test)
                RUN_TEST=true
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
    
    # 启动服务
    if ! start_server; then
        return 1
    fi
    
    return 0
}

# 执行主函数并返回退出码
main "$@"
exit $?