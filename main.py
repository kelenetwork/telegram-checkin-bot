# main.py
import asyncio
import signal
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from bot_manager import BotManager
from config_manager import ConfigManager

# 配置日志
def setup_logging():
    """设置日志配置"""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / 'app.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                           Telegram Auto Sender                              ║
║                              自动发送机器人                                    ║
║                                                                              ║
║  功能特性：                                                                    ║
║  • 定时自动发送消息                                                            ║
║  • 支持多种调度方式                                                            ║
║  • 完整的用户权限管理                                                          ║
║  • 详细的统计和日志                                                            ║
║  • 友好的Telegram Bot界面                                                      ║
║                                                                              ║
║  版本：v1.0.0                                                                 ║
║  作者：AI Assistant                                                          ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_config():
    """检查配置文件"""
    config_file = Path("config.json")
    
    if not config_file.exists():
        print("❌ 配置文件不存在！")
        print("请创建 config.json 文件，参考 config.json.example")
        return False
        
    # 检查必要的配置
    try:
        config = ConfigManager()
        
        if not config.get_bot_token():
            print("❌ 请在配置文件中设置 BOT_TOKEN")
            return False
            
        if not config.get_api_id() or not config.get_api_hash():
            print("❌ 请在配置文件中设置 API_ID 和 API_HASH")
            return False
            
        admin_users = config.get_admin_users()
        if not admin_users:
            print("⚠️  警告：未设置管理员用户，请在配置文件中设置 admin_users")
            
        return True
        
    except Exception as e:
        print(f"❌ 配置文件检查失败: {e}")
        return False

async def main():
    """主函数"""
    # 打印横幅
    print_banner()
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    # 检查配置
    if not check_config():
        sys.exit(1)
    
    logger.info("🚀 启动 Telegram Auto Sender...")
    
    # 创建机器人实例
    bot_manager = None
    
    def signal_handler(signum, frame):
        """信号处理器"""
        logger.info(f"🛑 收到信号 {signum}，正在停止...")
        if bot_manager:
            asyncio.create_task(bot_manager.stop_bot())
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 创建并启动机器人
        bot_manager = BotManager()
        
        if await bot_manager.start_bot():
            logger.info("✅ 机器人启动成功")
            
            # 保持运行
            while bot_manager.is_running:
                await asyncio.sleep(1)
        else:
            logger.error("❌ 机器人启动失败")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 收到键盘中断，正在停止...")
    except Exception as e:
        logger.error(f"❌ 运行时错误: {e}")
        sys.exit(1)
    finally:
        if bot_manager:
            await bot_manager.stop_bot()
        logger.info("👋 程序已退出")

def run():
    """运行函数"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {e}")

if __name__ == "__main__":
    run()

