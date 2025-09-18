#!/bin/bash
# run.sh - 简单启动脚本

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 启动 Telegram Auto Sender...${NC}"

# 检查配置文件
if [ ! -f "config.json" ]; then
    echo -e "${RED}❌ config.json 不存在！${NC}"
    echo -e "${YELLOW}请先运行: ./install.sh${NC}"
    exit 1
fi

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 未安装${NC}"
    exit 1
fi

# 检查依赖
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt 不存在${NC}"
    exit 1
fi

# 创建必要目录
directories=("data" "logs" "sessions")
for dir in "${directories[@]}"; do
    [ ! -d "$dir" ] && mkdir -p "$dir"
done

# 处理命令行参数
case "${1:-}" in
    "start"|"")
        echo -e "${BLUE}📋 启动模式: 前台运行${NC}"
        python3 main.py
        ;;
    "daemon"|"-d"|"--daemon")
        echo -e "${BLUE}📋 启动模式: 后台运行${NC}"
        nohup python3 main.py > logs/app.log 2>&1 &
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
            pkill -f "python3 main.py"
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
            # 检查是否有相关进程
            if pgrep -f "python3 main.py" > /dev/null; then
                echo -e "${YELLOW}但发现相关进程:${NC}"
                pgrep -f "python3 main.py" | xargs ps -p
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
    "test")
        echo -e "${BLUE}🧪 运行配置测试...${NC}"
        python3 -c "
import sys
sys.path.insert(0, '.')
from config_manager import ConfigManager

try:
    config = ConfigManager()
    print('✅ 配置管理器测试通过')
except Exception as e:
    print(f'❌ 配置测试失败: {e}')
    sys.exit(1)
"
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
        echo "  test       运行配置测试"
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
