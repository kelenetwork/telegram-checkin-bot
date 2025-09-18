#!/bin/bash
# install.sh - Telegram Auto Sender 安装脚本 (支持虚拟环境)

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
    echo -e "${GREEN}[INFO]${NC} \$1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} \$1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} \$1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} \$1"
}

# 检测操作系统
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
    elif [ -f /etc/redhat-release ]; then
        OS="CentOS"
        VER=$(grep -oE '[0-9]+\.[0-9]+' /etc/redhat-release)
    else
        OS=$(uname -s)
        VER=$(uname -r)
    fi
    
    log_info "检测到系统: $OS $VER"
}

# 检查系统要求
check_system() {
    log_step "检查系统环境..."
    
    # 检测操作系统
    detect_os
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    log_info "Python 版本: $python_version"
    
    # 检查Python版本
    if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)'; then
        log_error "需要 Python 3.8 或更高版本"
        exit 1
    fi
    
    # 检查是否需要安装 python3-venv
    if [[ "$OS" == *"Ubuntu"* ]] || [[ "$OS" == *"Debian"* ]]; then
        if ! python3 -m venv --help &> /dev/null; then
            log_info "安装 python3-venv..."
            apt update
            apt install -y python3-venv python3-full
        fi
    fi
    
    log_info "✅ 系统环境检查通过"
}

# 创建虚拟环境
create_venv() {
    log_step "创建 Python 虚拟环境..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        log_info "✅ 虚拟环境创建完成"
    else
        log_info "虚拟环境已存在"
    fi
}

# 安装依赖
install_dependencies() {
    log_step "安装 Python 依赖..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "requirements.txt 文件不存在"
        exit 1
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    
    # 升级pip
    log_info "升级 pip..."
    python -m pip install --upgrade pip
    
    # 安装依赖
    log_info "安装项目依赖..."
    pip install -r requirements.txt
    
    deactivate
    
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
            echo
            log_warn "⚠️  请编辑 config.json 文件，填入您的配置信息："
            echo -e "${YELLOW}  1. bot_token: 从 @BotFather 获取的机器人令牌${NC}"
            echo -e "${YELLOW}  2. api_id: 从 https://my.telegram.org/apps 获取${NC}"
            echo -e "${YELLOW}  3. api_hash: 从 https://my.telegram.org/apps 获取${NC}"
            echo -e "${YELLOW}  4. admin_users: 您的用户ID（从 @userinfobot 获取）${NC}"
            echo
        else
            log_warn "配置模板文件不存在，创建默认配置..."
            create_default_config
        fi
    else
        log_info "配置文件 config.json 已存在"
    fi
}

# 创建默认配置
create_default_config() {
    cat > config.json << 'EOF'
{
  "bot_token": "YOUR_BOT_TOKEN_HERE",
  "api_id": 12345678,
  "api_hash": "your_api_hash_here",
  "admin_users": [123456789],
  "settings": {
    "timezone": "Asia/Shanghai",
    "language": "zh_CN",
    "max_tasks_per_user": 50,
    "min_interval_seconds": 60,
    "session_timeout_hours": 24,
    "enable_user_registration": true,
    "log_level": "INFO"
  },
  "security": {
    "rate_limit": {
      "enabled": true,
      "requests_per_minute": 20
    },
    "whitelist_enabled": false,
    "whitelist": []
  },
  "database": {
    "type": "sqlite",
    "path": "data/bot.db"
  }
}
EOF
    log_info "已创建默认配置文件 config.json"
}

# 检查配置文件
check_config() {
    log_step "检查配置文件..."
    
    if [ ! -f "config.json" ]; then
        log_error "配置文件 config.json 不存在"
        return 1
    fi
    
    # 使用虚拟环境中的Python检查配置
    source venv/bin/activate
    python -c "
import json
import sys

try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # 检查必要字段
    required_fields = ['bot_token', 'api_id', 'api_hash']
    missing_fields = []
    
    for field in required_fields:
        value = config.get(field)
        if not value or str(value) in ['YOUR_BOT_TOKEN_HERE', 'your_api_hash_here', '12345678']:
            missing_fields.append(field)
    
    if missing_fields:
        print(f'❌ 需要配置以下字段: {', '.join(missing_fields)}')
        print('请编辑 config.json 文件，填入正确的配置信息')
        sys.exit(1)
    
    print('✅ 配置文件格式正确')
    
except json.JSONDecodeError as e:
    print(f'❌ 配置文件JSON格式错误: {e}')
    sys.exit(1)
except Exception as e:
    print(f'❌ 配置文件检查失败: {e}')
    sys.exit(1)
" 2>/dev/null || log_warn "配置文件需要完善，请填入正确的配置信息"
    deactivate
}

# 创建运行脚本
create_run_script() {
    log_step "创建运行脚本..."
    
    cat > run.sh << 'EOF'
#!/bin/bash
# run.sh - Telegram Auto Sender 启动脚本 (虚拟环境版)

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 启动 Telegram Auto Sender...${NC}"

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ 虚拟环境不存在！${NC}"
    echo -e "${YELLOW}请先运行: ./install.sh${NC}"
    exit 1
fi

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo -e "${RED}❌ config.json 不存在！${NC}"
    echo -e "${YELLOW}请先运行: ./install.sh${NC}"
    exit 1
fi

# 创建必要目录
directories=("data" "logs" "sessions")
for dir in "${directories[@]}"; do
    [ ! -d "$dir" ] && mkdir -p "$dir"
done

# 激活虚拟环境
source venv/bin/activate

# 处理命令行参数
case "${1:-}" in
    "start"|"")
        echo -e "${BLUE}📋 启动模式: 前台运行${NC}"
        python main.py
        ;;
    "daemon"|"-d"|"--daemon")
        echo -e "${BLUE}📋 启动模式: 后台运行${NC}"
        nohup python main.py > logs/app.log 2>&1 &
        echo $! > .pid
        echo -e "${GREEN}✅ 程序已在后台启动，PID: $(cat .pid)${NC}"
        echo -e "${BLUE}💡 查看日志: tail -f logs/app.log${NC}"
        echo -e "${BLUE}💡 停止程序: ./run.sh stop${NC}"
        ;;
    "stop")
        if [ -f ".pid" ]; then
            pid=$(cat .pid)
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                rm .pid
                echo -e "${GREEN}✅ 程序已停止${NC}"
            else
                echo -e "${YELLOW}⚠️ 程序未运行或PID无效${NC}"
                rm .pid
            fi
        else
            echo -e "${YELLOW}⚠️ 未找到PID文件，尝试根据进程名停止...${NC}"
            pkill -f "python main.py"
        fi
        ;;
    "restart")
        echo -e "${BLUE}🔄 重启程序...${NC}"
        ./run.sh stop
        sleep 2
        ./run.sh daemon
        ;;
    "status")
        if [ -f ".pid" ]; then
            pid=$(cat .pid)
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${GREEN}✅ 程序正在运行，PID: $pid${NC}"
                ps -p "$pid" -o pid,ppid,cmd
            else
                echo -e "${RED}❌ 程序未运行${NC}"
                rm .pid
            fi
        else
            echo -e "${YELLOW}⚠️ 未找到PID文件${NC}"
            if pgrep -f "python main.py" > /dev/null; then
                echo -e "${YELLOW}但发现相关进程:${NC}"
                pgrep -f "python main.py" | xargs ps -p
            else
                echo -e "${RED}❌ 程序未运行${NC}"
            fi
        fi
        ;;
    "logs")
        if [ -f "logs/app.log" ]; then
            tail -f logs/app.log
        else
            echo -e "${RED}❌ 日志文件不存在${NC}"
        fi
        ;;
    "shell")
        echo -e "${BLUE}🐚 进入虚拟环境 Shell...${NC}"
        echo -e "${YELLOW}退出请输入: exit${NC}"
        bash --init-file <(echo "source venv/bin/activate")
        ;;
    "install")
        echo -e "${BLUE}📦 重新安装依赖...${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}✅ 依赖重新安装完成${NC}"
        ;;
    "help"|"-h"|"--help")
        echo -e "${BLUE}Telegram Auto Sender 启动脚本${NC}"
        echo
        echo "用法: ./run.sh [命令]"
        echo
        echo "命令:"
        echo "  start      前台启动程序 (默认)"
        echo "  daemon     后台启动程序"
        echo "  stop       停止后台程序"
        echo "  restart    重启后台程序"
        echo "  status     查看程序状态"
        echo "  logs       查看实时日志"
        echo "  shell      进入虚拟环境Shell"
        echo "  install    重新安装依赖"
        echo "  help       显示此帮助信息"
        echo
        echo "示例:"
        echo "  ./run.sh                # 前台启动"
        echo "  ./run.sh daemon         # 后台启动"
        echo "  ./run.sh logs           # 查看日志"
        ;;
    *)
        echo -e "${RED}❌ 未知命令: $1${NC}"
        echo -e "${YELLOW}使用 ./run.sh help 查看帮助${NC}"
        exit 1
        ;;
esac

# 退出虚拟环境
deactivate 2>/dev/null || true
EOF

    chmod +x run.sh
    log_info "已创建 run.sh 启动脚本"
}

# 创建服务管理脚本
create_service_script() {
    log_step "创建服务管理脚本..."
    
    cat > service.sh << 'EOF'
#!/bin/bash
# service.sh - 系统服务管理脚本

SERVICE_NAME="telegram-auto-sender"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
WORK_DIR="$(pwd)"

create_service() {
    echo "创建系统服务..."
    
    sudo tee "$SERVICE_FILE" > /dev/null << EOL
[Unit]
Description=Telegram Auto Sender Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORK_DIR
Environment=PATH=$WORK_DIR/venv/bin
ExecStart=$WORK_DIR/venv/bin/python $WORK_DIR/main.py
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

    sudo systemctl daemon-reload
    sudo systemctl enable "$SERVICE_NAME"
    echo "✅ 系统服务创建完成"
}

case "$1" in
    "install")
        create_service
        ;;
    "start")
        sudo systemctl start "$SERVICE_NAME"
        echo "✅ 服务已启动"
        ;;
    "stop")
        sudo systemctl stop "$SERVICE_NAME"
        echo "✅ 服务已停止"
        ;;
    "restart")
        sudo systemctl restart "$SERVICE_NAME"
        echo "✅ 服务已重启"
        ;;
    "status")
        sudo systemctl status "$SERVICE_NAME"
        ;;
    "enable")
        sudo systemctl enable "$SERVICE_NAME"
        echo "✅ 服务已设为开机自启"
        ;;
    "disable")
        sudo systemctl disable "$SERVICE_NAME"
        echo "✅ 服务已取消开机自启"
        ;;
    "remove")
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo rm -f "$SERVICE_FILE"
        sudo systemctl daemon-reload
        echo "✅ 系统服务已删除"
        ;;
    "logs")
        sudo journalctl -u "$SERVICE_NAME" -f
        ;;
    *)
        echo "用法: ./service.sh {install|start|stop|restart|status|enable|disable|remove|logs}"
        echo
        echo "命令说明:"
        echo "  install  - 创建系统服务"
        echo "  start    - 启动服务"
        echo "  stop     - 停止服务"
        echo "  restart  - 重启服务"
        echo "  status   - 查看服务状态"
        echo "  enable   - 设置开机自启"
        echo "  disable  - 取消开机自启"
        echo "  remove   - 删除系统服务"
        echo "  logs     - 查看服务日志"
        ;;
esac
EOF

    chmod +x service.sh
    log_info "已创建 service.sh 服务管理脚本"
}

# 主安装函数
main() {
    print_banner
    
    log_info "开始安装 Telegram Auto Sender..."
    
    # 检查系统
    check_system
    
    # 创建虚拟环境
    create_venv
    
    # 安装依赖
    install_dependencies
    
    # 创建目录结构
    create_directories
    
    # 配置文件设置
    setup_config
    
    # 检查配置文件（可能需要用户手动配置）
    check_config
    
    # 创建运行脚本
    create_run_script
    
    # 创建服务管理脚本
    create_service_script
    
    # 设置权限
    chmod 755 *.sh
    
    echo
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║                            🎉 安装完成！                                      ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${BLUE}📋 下一步操作：${NC}"
    echo
    echo -e "${YELLOW}1. 编辑配置文件：${NC}"
    echo -e "   nano config.json"
    echo -e "   # 填入您的 bot_token, api_id, api_hash 和 admin_users"
    echo
    echo -e "${YELLOW}2. 启动程序：${NC}"
    echo -e "   ./run.sh                 # 前台运行"
    echo -e "   ./run.sh daemon          # 后台运行"
    echo
    echo -e "${YELLOW}3. 查看帮助：${NC}"
    echo -e "   ./run.sh help            # 查看启动脚本帮助"
    echo -e "   ./service.sh install     # 安装为系统服务（可选）"
    echo
    echo -e "${BLUE}📖 获取配置信息：${NC}"
    echo -e "   • Bot Token: 向 @BotFather 发送 /newbot"
    echo -e "   • API ID/Hash: 访问 https://my.telegram.org/apps"
    echo -e "   • 用户ID: 向 @userinfobot 发送任意消息"
    echo
    echo -e "${GREEN}✨ 安装成功！祝您使用愉快！${NC}"
}

# 运行主函数
main "$@"
