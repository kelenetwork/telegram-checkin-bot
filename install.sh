#!/bin/bash

# Telegram Auto Check-in Bot 一键安装脚本
# 支持 Ubuntu/Debian/CentOS/RHEL/Fedora
# 支持 root 和普通用户

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的信息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# 检测系统类型
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
        VER=$(lsb_release -sr)
    else
        print_error "无法检测系统类型"
        exit 1
    fi
}

# 检查 Python 版本
check_python() {
    print_info "检查 Python 版本..."
    
    # 检查 python3
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
            print_success "Python 版本符合要求: $PYTHON_VERSION"
            PYTHON_CMD="python3"
            return 0
        else
            print_warning "Python 版本过低: $PYTHON_VERSION，需要安装 Python 3.8+"
        fi
    fi
    
    # 需要安装 Python
    return 1
}

# 运行命令（自动处理 root/sudo）
run_cmd() {
    if [ "$EUID" -eq 0 ]; then
        # 是 root 用户，直接运行
        "$@"
    else
        # 非 root 用户，使用 sudo
        sudo "$@"
    fi
}

# 安装 Python 3.8+
install_python() {
    print_info "安装 Python 3.8+..."
    
    case $OS in
        ubuntu|debian)
            run_cmd apt-get update -qq
            run_cmd apt-get install -y python3 python3-venv python3-pip
            ;;
        centos|rhel|fedora)
            if [ "$VER" -ge 8 ]; then
                run_cmd dnf install -y python38 python38-devel
            else
                run_cmd yum install -y centos-release-scl
                run_cmd yum install -y rh-python38 rh-python38-python-devel
                source /opt/rh/rh-python38/enable
            fi
            ;;
        *)
            print_error "不支持的系统: $OS"
            exit 1
            ;;
    esac
}

# 安装系统依赖
install_dependencies() {
    print_info "安装系统依赖..."
    
    case $OS in
        ubuntu|debian)
            run_cmd apt-get update -qq
            run_cmd apt-get install -y git curl wget gcc python3-dev screen
            ;;
        centos|rhel|fedora)
            run_cmd yum install -y git curl wget gcc python3-devel screen
            ;;
        *)
            print_error "不支持的系统: $OS"
            exit 1
            ;;
    esac
    
    print_success "系统依赖安装完成"
}

# 克隆项目
clone_project() {
    print_info "下载项目代码..."
    
    # 如果已经在项目目录中，跳过克隆
    if [ -f "main.py" ] && [ -f "requirements.txt" ]; then
        print_info "已在项目目录中，跳过下载"
        PROJECT_DIR=$(pwd)
    else
        # 克隆项目
        if [ -d "telegram-checkin-bot" ]; then
            print_warning "项目目录已存在，更新代码..."
            cd telegram-checkin-bot
            git pull
            cd ..
        else
            git clone https://github.com/kelenetwork/telegram-checkin-bot.git
        fi
        PROJECT_DIR=$(pwd)/telegram-checkin-bot
        cd $PROJECT_DIR
    fi
    
    print_success "项目代码准备完成"
}

# 设置虚拟环境
setup_venv() {
    print_info "设置 Python 虚拟环境..."
    
    # 删除旧的虚拟环境（如果存在）
    if [ -d "venv" ]; then
        print_warning "删除旧的虚拟环境..."
        rm -rf venv
    fi
    
    # 创建虚拟环境
    $PYTHON_CMD -m venv venv
    
    # 激活虚拟环境
    source venv/bin/activate
    
    # 升级 pip
    pip install --upgrade pip wheel setuptools
    
    print_success "虚拟环境设置完成"
}

# 安装 Python 包
install_packages() {
    print_info "安装 Python 依赖包..."
    
    # 使用国内镜像加速（如果在中国）
    if curl -s --connect-timeout 3 https://pypi.doubanio.com &> /dev/null; then
        print_info "使用豆瓣镜像加速下载..."
        pip config set global.index-url https://pypi.doubanio.com/simple
    fi
    
    # 安装依赖
    pip install -r requirements.txt
    
    print_success "Python 依赖安装完成"
}

# 创建启动脚本
create_start_script() {
    print_info "创建启动脚本..."
    
    cat > start.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate
python main.py
EOF
    
    chmod +x start.sh
    
    print_success "启动脚本创建完成"
}

# 创建 systemd 服务
create_systemd_service() {
    print_info "创建 systemd 服务..."
    
    # 获取当前用户和路径
    CURRENT_USER=$(whoami)
    WORK_DIR=$(pwd)
    
    # 创建服务文件
    run_cmd tee /etc/systemd/system/telegram-checkin-bot.service > /dev/null << EOF
[Unit]
Description=Telegram Auto Check-in Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$WORK_DIR
Environment="PATH=$WORK_DIR/venv/bin"
ExecStart=$WORK_DIR/venv/bin/python $WORK_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=append:$WORK_DIR/bot.log
StandardError=append:$WORK_DIR/bot.log

[Install]
WantedBy=multi-user.target
EOF
    
    # 重载 systemd
    run_cmd systemctl daemon-reload
    
    print_success "Systemd 服务创建完成"
}

# 显示完成信息
show_completion_info() {
    echo
    print_success "🎉 安装完成！"
    echo
    echo -e "${GREEN}接下来的步骤：${NC}"
    echo
    echo "1. 直接运行（前台模式）："
    echo "   cd $PROJECT_DIR"
    echo "   ./start.sh"
    echo
    echo "2. 使用 screen 后台运行："
    echo "   cd $PROJECT_DIR"
    echo "   screen -S telegram-bot"
    echo "   ./start.sh"
    echo "   # 按 Ctrl+A 然后按 D 分离会话"
    echo
    if [ "$EUID" -eq 0 ]; then
        echo "3. 使用 systemd 服务（推荐）："
        echo "   systemctl start telegram-checkin-bot"
        echo "   systemctl enable telegram-checkin-bot  # 开机自启"
        echo "   systemctl status telegram-checkin-bot   # 查看状态"
    else
        echo "3. 使用 systemd 服务（推荐）："
        echo "   sudo systemctl start telegram-checkin-bot"
        echo "   sudo systemctl enable telegram-checkin-bot  # 开机自启"
        echo "   sudo systemctl status telegram-checkin-bot   # 查看状态"
    fi
    echo
    echo -e "${YELLOW}首次运行需要配置以下信息：${NC}"
    echo "   - Bot Token (从 @BotFather 获取)"
    echo "   - Telegram ID (从 @userinfobot 获取)"
    echo "   - API ID 和 Hash (从 https://my.telegram.org 获取)"
    echo "   - 手机号码"
    echo
    
    if [ "$EUID" -eq 0 ]; then 
        echo
        print_warning "⚠️  注意：您使用 root 用户安装"
        print_warning "建议创建普通用户运行服务以提高安全性"
        echo
        echo "创建运行用户的命令："
        echo "   useradd -m -s /bin/bash telegram"
        echo "   chown -R telegram:telegram $PROJECT_DIR"
        echo "   # 然后修改 systemd 服务文件中的 User=telegram"
    fi
}

# 主函数
main() {
    clear
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}  Telegram Auto Check-in Bot 安装器  ${NC}"
    echo -e "${BLUE}======================================${NC}"
    echo
    
    # 检测系统
    detect_os
    print_info "检测到系统: $OS $VER"
    
    # 提示用户权限信息
    if [ "$EUID" -eq 0 ]; then 
        print_info "以 root 用户身份运行"
    else
        print_info "以普通用户身份运行"
        # 检查 sudo 权限
        if ! sudo -n true 2>/dev/null; then
            print_warning "需要 sudo 权限来安装系统依赖"
            sudo -v
        fi
    fi
    
    # 安装系统依赖
    install_dependencies
    
    # 检查并安装 Python
    if ! check_python; then
        install_python
        # 重新检查
        if ! check_python; then
            print_error "Python 安装失败"
            exit 1
        fi
    fi
    
    # 克隆项目
    clone_project
    
    # 设置虚拟环境
    setup_venv
    
    # 安装 Python 包
    install_packages
    
    # 创建启动脚本
    create_start_script
    
    # 询问是否创建 systemd 服务
    echo
    read -p "是否创建 systemd 服务？[y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        create_systemd_service
    fi
    
    # 显示完成信息
    show_completion_info
}

# 运行主函数
main
