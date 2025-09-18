#!/bin/bash

# Telegram Bot 快速启动脚本

WORK_DIR="/opt/telegram_bot"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查安装
check_installation() {
    if [ ! -d "$WORK_DIR" ]; then
        print_error "Bot 未安装，请先运行安装脚本"
        exit 1
    fi
    
    cd $WORK_DIR
}

# 配置向导
setup_wizard() {
    print_info "Telegram Bot 配置向导"
    echo "========================================"
    echo ""
    echo "📋 需要准备的信息:"
    echo "1. API ID - 从 https://my.telegram.org/apps 获取"
    echo "2. API Hash - 从 https://my.telegram.org/apps 获取"
    echo "3. Bot Token - 可选，从 @BotFather 获取"
    echo ""
    read -p "是否继续配置? (y/n): " -n 1 -r
    echo ""
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        python3 telegram_bot.py
    else
        print_info "配置已取消"
        exit 0
    fi
}

# 快速启动
quick_start() {
    if [ ! -f "bot_config.json" ]; then
        print_info "未找到配置文件，启动配置向导..."
        setup_wizard
    else
        print_info "发现配置文件，启动Bot..."
        choice_menu
    fi
}

# 选择菜单
choice_menu() {
    echo ""
    echo "🎮 选择启动方式:"
    echo "========================================"
    echo "1. 交互式运行 (前台运行，可看到实时输出)"
    echo "2. 服务模式运行 (后台运行)"
    echo "3. 重新配置"
    echo "4. 查看状态"
    echo "5. 退出"
    echo ""
    
    read -p "请选择 (1-5): " choice
    
    case $choice in
        1)
            print_info "启动交互式模式..."
            python3 telegram_bot.py
            ;;
        2)
            print_info "启动服务模式..."
            systemctl start telegram-bot
            systemctl enable telegram-bot
            print_success "Bot 已在后台启动"
            systemctl status telegram-bot --no-pager
            ;;
        3)
            print_info "重新配置..."
            rm -f bot_config.json
            setup_wizard
            ;;
        4)
            print_info "查看Bot状态..."
            tgbot status
            ;;
        5)
            print_info "退出"
            exit 0
            ;;
        *)
            print_error "无效选择，请重试"
            choice_menu
            ;;
    esac
}

# 主函数
main() {
    echo "🎉 Telegram 自动签到 Bot"
    echo "========================================"
    
    check_installation
    quick_start
}

# 运行
main
