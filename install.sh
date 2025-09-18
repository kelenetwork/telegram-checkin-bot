#!/bin/bash
# install.sh - Telegram Auto Sender 安装启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印横幅
print_banner() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════════════════════╗"
    echo "║                           Telegram Auto Sender                              ║"
    echo "║                              自动发送机器人                                    ║"
    echo "║                                安装脚本                                       ║"
    echo "╚══════════════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 检查系统要求
check_system() {
    log_step "检查系统环境..."
    
    # 检查操作系统
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        log_info "检测到 Linux 系统"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        log_info "检测到 macOS 系统"
    else
        log_warn "未知操作系统: $OSTYPE"
    fi
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装，请先安装 Python 3.8+"
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_info "Python 版本: $python_version"
    
    # 检查Python版本
    if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
        log_error "需要 Python 3.8 或更高版本"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 未安装"
        exit 1
    fi
    
    log_info "✅ 系统环境检查通过"
}

# 安装依赖
install_dependencies() {
    log_step "安装 Python 依赖..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 升级pip
    log_info "升级 pip..."
    python3 -m pip install --upgrade pip
    
    # 安装依赖
    log_info "安装项目依赖..."
    pip3 install -r requirements.txt
    
    log_info "✅ 依赖安装完成"
}

# 创建目录结构
create_directories() {
    log_step "创建目录结构..."
    
    directories=("data" "logs" "sessions" "temp" "backups")
    
    for dir in "${directories[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_info "创建目录: $dir"
        fi
    done
    
    log_info "✅ 目录结构创建完成"
}

# 配置文件设置
setup_config() {
    log_step "配置文件设置..."
    
    if [ ! -f "config.json" ]; then
        if [ -f "config.json.example" ]; then
            cp config.json.example config.json
            log_info "已复制配置模板到 config.json"
            log_warn "请编辑 config.json 文件，填入您的配置信息："
            log_warn "  - BOT_TOKEN: Telegram Bot Token"
            log_warn "  - API_ID: Telegram API ID"
            log_warn "  - API_HASH: Telegram API Hash"
            log_warn "  - admin_users: 管理员用户ID列表"
        else
            log_error "配置模板文件 config.json.example 不存在"
            exit 1
        fi
    else
        log_info "配置文件 config.json 已存在"
    fi
}

# 检查配置文件
check_config() {
    log_step "检查配置文件..."
    
    if [ ! -f "config.json" ]; then
        log_error "配置文件 config.json 不存在"
        return 1
    fi
    
    # 使用Python检查配置
    python3 -c "
import json
import sys

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 检查必要字段
    required_fields = ['bot_token', 'api_id', 'api_hash']
    missing_fields = []
    
    for field in required_fields:
        if not config.get(field) or config.get(field) == 'YOUR_${field.upper()}_HERE':
            missing_fields.append(field)
    
    if missing_fields:
        print(f'❌ 缺少必要配置: {', '.join(missing_fields)}')
        sys.exit(1)
    
    print('✅ 配置文件检查通过')
    
except json.JSONDecodeError as e:
    print(f'❌ 配置文件JSON格式错误: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ 配置文件检查失败: {e}')
    sys.exit(1)
"
    
    if [ $? -ne 0 ]; then
        log_error "配置文件检查失败，请检查并修正配置"
        return 1
    fi
    
    return 0
}

# 创建服务文件 (systemd)
create_systemd_service() {
    log_step "创建系统服务..."
    
    if ! command -v systemctl &> /dev/null; then
        log_warn "systemd 不可用，跳过服务创建"
        return
    fi
    
    read -p "是否创建系统服务 (systemd)? [y/N]: " create_service
    
    if [[ $create_service =~ ^[Yy]$ ]]; then
        current_dir=$(pwd)
        current_user=$(whoami)
        
        service_file="/etc/systemd/system/telegram-auto-sender.service"
        
        sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=Telegram Auto Sender Bot
After=network.target

[Service]
Type=simple
User=$current_user
WorkingDirectory=$current_dir
ExecStart=$(which python3) $current_dir/main.py
Restart=always
RestartSec=5
Environment=PYTHONPATH=$current_dir
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
        
        sudo systemctl daemon-reload
        sudo systemctl enable telegram-auto-sender
        
        log_info "系统服务已创建: telegram-auto-sender"
        log_info "使用以下命令管理服务:"
        log_info "  启动: sudo systemctl start telegram-auto-sender"
        log_info "  停止: sudo systemctl stop telegram-auto-sender"
        log_info "  查看状态: sudo systemctl status telegram-auto-sender"
        log_info "  查看日志: sudo journalctl -u telegram-auto-sender -f"
    fi
}

# 运行测试
run_test() {
    log_step "运行配置测试..."
    
    python3 -c "
import sys
sys.path.insert(0, '.')
from config_manager import ConfigManager

try:
    config = ConfigManager()
    print('✅ 配置管理器初始化成功')
    
    # 测试基本功能
    bot_token = config.get_bot_token()
    if bot_token and bot_token != 'YOUR_BOT_TOKEN_HERE':
        print('✅ Bot Token 配置正确')
    else:
        print('❌ Bot Token 未配置或配置错误')
        sys.exit(1)
    
    api_id = config.get_api_id()
    api_hash = config.get_api_hash()
    if api_id and api_hash and api_hash != 'YOUR_API_HASH_HERE':
        print('✅ API 配置正确')
    else:
        print('❌ API 配置未配置或配置错误')
        sys.exit(1)
    
    print('✅ 所有基础配置检查通过')
    
except Exception as e:
    print(f'❌ 配置测试失败: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        log_info "✅ 配置测试通过"
    else
        log_error "配置测试失败"
        return 1
    fi
}

# 启动程序
start_program() {
    log_step "启动程序..."
    
    read -p "是否立即启动程序? [y/N]: " start_now
    
    if [[ $start_now =~ ^[Yy]$ ]]; then
        log_info "启动 Telegram Auto Sender..."
        python3 main.py
    else
        log_info "程序未启动，您可以稍后使用以下命令启动:"
        log_info "  python3 main.py"
        log_info "或者使用后台运行:"
        log_info "  nohup python3 main.py > logs/app.log 2>&1 &"
    fi
}

# 显示使用说明
show_usage() {
    echo
    log_info "🎉 安装完成！"
    echo
    echo -e "${BLUE}使用说明:${NC}"
    echo "1. 编辑 config.json 文件，填入正确的配置信息"
    echo "2. 运行程序: python3 main.py"
    echo "3. 在Telegram中找到您的Bot，发送 /start 开始使用"
    echo
    echo -e "${BLUE}目录说明:${NC}"
    echo "  config.json     - 主配置文件"
    echo "  data/          - 数据存储目录"
    echo "  logs/          - 日志文件目录"
    echo "  sessions/      - Telegram会话文件"
    echo "  temp/          - 临时文件目录"
    echo "  backups/       - 备份文件目录"
    echo
    echo -e "${BLUE}常用命令:${NC}"
    echo "  启动程序: python3 main.py"
    echo "  后台运行: nohup python3 main.py > logs/app.log 2>&1 &"
    echo "  查看日志: tail -f logs/app.log"
    echo
    echo -e "${BLUE}获取帮助:${NC}"
    echo "  项目地址: https://github.com/your-repo"
    echo "  问题反馈: https://github.com/your-repo/issues"
    echo
}

# 主函数
main() {
    print_banner
    
    log_info "开始安装 Telegram Auto Sender..."
    
    # 检查系统环境
    check_system
    
    # 安装依赖
    install_dependencies
    
    # 创建目录结构
    create_directories
    
    # 配置文件设置
    setup_config
    
    # 等待用户配置
    if [ ! -f "config.json" ] || ! check_config; then
        echo
        log_warn "请编辑 config.json 文件，填入正确的配置信息后重新运行此脚本"
        echo
        echo -e "${YELLOW}配置步骤:${NC}"
        echo "1. 获取 Bot Token: 向 @BotFather 创建机器人"
        echo "2. 获取 API ID 和 API Hash: 访问 https://my.telegram.org/apps"
        echo "3. 获取用户ID: 向 @userinfobot 发送消息"
        echo "4. 编辑 config.json 文件，替换相应的配置项"
        echo
        echo "配置完成后运行: ./install.sh --check"
        exit 0
    fi
    
    # 运行测试
    run_test
    
    # 创建系统服务
    create_systemd_service
    
    # 显示使用说明
    show_usage
    
    # 询问是否启动
    start_program
}

# 处理命令行参数
case "${1:-}" in
    "--check")
        log_info "检查配置..."
        if check_config && run_test; then
            log_info "✅ 配置检查通过，可以启动程序"
        else
            log_error "❌ 配置检查失败"
            exit 1
        fi
        ;;
    "--start")
        log_info "启动程序..."
        if check_config && run_test; then
            python3 main.py
        else
            log_error "❌ 配置检查失败，无法启动"
            exit 1
        fi
        ;;
    "--help")
        echo "Telegram Auto Sender 安装脚本"
        echo
        echo "用法: ./install.sh [选项]"
        echo
        echo "选项:"
        echo "  (无参数)   完整安装过程"
        echo "  --check    仅检查配置"
        echo "  --start    检查配置并启动程序" 
        echo "  --help     显示此帮助信息"
        ;;
    *)
        main
        ;;
esac
