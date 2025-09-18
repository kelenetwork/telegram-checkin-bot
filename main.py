#!/usr/bin/env python3
"""
Telegram 自动签到机器人主程序
"""

import asyncio
import sys
import os
import signal
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.config import load_config
from utils.logger import setup_logging
from utils.permissions import init_permissions
from core.database import init_database
from core.scheduler import TaskScheduler
from bot.bot_client import BotManager
from bot.commands import CommandHandler
from bot.callbacks import CallbackHandler
from bot.handlers import MessageHandler, ErrorHandler

class TelegramCheckinBot:
    """Telegram签到机器人主类"""
    
    def __init__(self):
        self.config = None
        self.bot_manager = None
        self.scheduler = None
        self.logger = None
        self.running = False
    
    async def initialize(self):
        """初始化所有组件"""
        try:
            # 加载配置
            self.config = load_config()
            
            # 设置日志
            self.logger = setup_logging(self.config)
            self.logger.info("🚀 启动Telegram签到机器人...")
            
            # 初始化权限系统
            init_permissions(self.config)
            self.logger.info("✅ 权限系统初始化完成")
            
            # 初始化数据库
            await init_database(self.config)
            self.logger.info("✅ 数据库初始化完成")
            
            # 初始化机器人管理器
            self.bot_manager = BotManager(self.config)
            await self.bot_manager.initialize()
            self.logger.info("✅ 机器人客户端初始化完成")
            
            # 注册处理器
            await self.register_handlers()
            self.logger.info("✅ 处理器注册完成")
            
            # 初始化任务调度器
            self.scheduler = TaskScheduler(self.config, self.bot_manager)
            await self.scheduler.initialize()
            self.logger.info("✅ 任务调度器初始化完成")
            
            self.logger.info("🎉 所有组件初始化完成!")
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"❌ 初始化失败: {e}")
            else:
                print(f"❌ 初始化失败: {e}")
            raise
    
    async def register_handlers(self):
        """注册所有处理器"""
        bot_client = self.bot_manager.get_bot_client()
        
        # 初始化处理器
        command_handler = CommandHandler(self.config, self.bot_manager)
        callback_handler = CallbackHandler(self.config, self.bot_manager)
        message_handler = MessageHandler(self.config, self.bot_manager)
        error_handler = ErrorHandler(self.config)
        
        # 注册命令处理器
        await command_handler.register_handlers(bot_client)
        
        # 注册回调处理器
        await callback_handler.register_handlers(bot_client)
        
        # 注册消息处理器
        await message_handler.register_handlers(bot_client)
        
        # 注册错误处理器
        await error_handler.register_handlers(bot_client)
    
    async def start(self):
        """启动机器人"""
        try:
            self.running = True
            
            # 启动机器人
            await self.bot_manager.start()
            self.logger.info("✅ 机器人已启动")
            
            # 启动调度器
            await self.scheduler.start()
            self.logger.info("✅ 任务调度器已启动")
            
            # 发送启动通知
            await self.send_startup_notification()
            
            self.logger.info("🎊 机器人运行中... 按 Ctrl+C 停止")
            
            # 保持运行
            while self.running:
                await asyncio.sleep(1)
                
        except Exception as e:
            self.logger.error(f"❌ 运行时错误: {e}")
            raise
    
    async def stop(self):
        """停止机器人"""
        try:
            self.running = False
            self.logger.info("🛑 正在停止机器人...")
            
            # 发送停止通知
            await self.send_shutdown_notification()
            
            # 停止调度器
            if self.scheduler:
                await self.scheduler.stop()
                self.logger.info("✅ 任务调度器已停止")
            
            # 停止机器人
            if self.bot_manager:
                await self.bot_manager.stop()
                self.logger.info("✅ 机器人已停止")
            
            self.logger.info("👋 机器人已完全停止")
            
        except Exception as e:
            self.logger.error(f"❌ 停止过程中发生错误: {e}")
    
    async def send_startup_notification(self):
        """发送启动通知"""
        try:
            admin_ids = self.config.get('telegram', {}).get('admin_ids', [])
            
            if admin_ids:
                message = "🎉 机器人已成功启动！\n\n" \
                         f"📊 状态: 运行中\n" \
                         f"⏰ 启动时间: {asyncio.get_event_loop().time()}\n" \
                         f"🔧 版本: v1.0.0"
                
                for admin_id in admin_ids:
                    try:
                        await self.bot_manager.send_message(admin_id, message)
                    except Exception as e:
                        self.logger.warning(f"无法向管理员 {admin_id} 发送启动通知: {e}")
                        
        except Exception as e:
            self.logger.warning(f"发送启动通知失败: {e}")
    
    async def send_shutdown_notification(self):
        """发送停止通知"""
        try:
            admin_ids = self.config.get('telegram', {}).get('admin_ids', [])
            
            if admin_ids:
                message = "🛑 机器人即将停止\n\n" \
                         f"📊 状态: 停止中\n" \
                         f"⏰ 停止时间: {asyncio.get_event_loop().time()}"
                
                for admin_id in admin_ids:
                    try:
                        await self.bot_manager.send_message(admin_id, message)
                    except Exception as e:
                        self.logger.warning(f"无法向管理员 {admin_id} 发送停止通知: {e}")
                        
        except Exception as e:
            self.logger.warning(f"发送停止通知失败: {e}")


# 全局机器人实例
bot_instance = None

def signal_handler(signum, frame):
    """信号处理器"""
    print(f"\n收到信号 {signum}，正在停止机器人...")
    
    if bot_instance:
        # 创建新的事件循环来运行停止协程
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(bot_instance.stop())
        loop.close()
    
    sys.exit(0)

def setup_signal_handlers():
    """设置信号处理器"""
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Windows下注册额外信号
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)

async def main():
    """主函数"""
    global bot_instance
    
    try:
        # 设置信号处理器
        setup_signal_handlers()
        
        # 创建机器人实例
        bot_instance = TelegramCheckinBot()
        
        # 初始化
        await bot_instance.initialize()
        
        # 启动
        await bot_instance.start()
        
    except KeyboardInterrupt:
        print("\n用户中断，正在停止...")
        if bot_instance:
            await bot_instance.stop()
    except Exception as e:
        print(f"❌ 程序异常: {e}")
        if bot_instance:
            await bot_instance.stop()
        sys.exit(1)

def check_environment():
    """检查运行环境"""
    print("🔍 检查运行环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print(f"❌ 需要Python 3.8或更高版本，当前版本: {sys.version}")
        sys.exit(1)
    
    # 检查必要文件
    required_files = ['.env', 'requirements.txt']
    for file in required_files:
        if not os.path.exists(file):
            print(f"❌ 缺少必要文件: {file}")
            if file == '.env':
                print("请先运行 python install.py 进行安装
                print("请先运行 python install.py 进行安装配置")
            sys.exit(1)
    
    # 检查必要目录
    required_dirs = ['data', 'logs']
    for directory in required_dirs:
        if not os.path.exists(directory):
            print(f"📁 创建目录: {directory}")
            os.makedirs(directory, exist_ok=True)
    
    print("✅ 环境检查通过")

def print_banner():
    """打印启动横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║            🤖 Telegram 自动签到机器人                       ║
║                                                              ║
║                    Auto Checkin Bot v1.0                    ║
║                                                              ║
║              🚀 正在启动，请稍候...                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def print_startup_info():
    """打印启动信息"""
    print("\n📋 启动信息:")
    print(f"   🐍 Python版本: {sys.version.split()[0]}")
    print(f"   📁 工作目录: {os.getcwd()}")
    print(f"   💾 平台: {sys.platform}")
    print(f"   🕒 启动时间: {asyncio.get_event_loop().time()}")
    print("\n💡 使用提示:")
    print("   - 按 Ctrl+C 可以安全停止机器人")
    print("   - 日志文件保存在 logs/ 目录下")
    print("   - 数据库文件保存在 data/ 目录下")
    print("   - 遇到问题请查看日志文件")

if __name__ == "__main__":
    try:
        # 打印横幅
        print_banner()
        
        # 检查环境
        check_environment()
        
        # 打印启动信息
        print_startup_info()
        
        # 运行主程序
        if sys.platform == 'win32':
            # Windows下设置事件循环策略
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        
        # 运行机器人
        asyncio.run(main())
        
    except Exception as e:
        print(f"\n💥 启动失败: {e}")
        print("\n🔧 可能的解决方案:")
        print("   1. 检查 .env 文件配置是否正确")
        print("   2. 确认网络连接正常")
        print("   3. 验证 Telegram Bot Token 是否有效")
        print("   4. 查看 logs/ 目录下的详细日志")
        sys.exit(1)

