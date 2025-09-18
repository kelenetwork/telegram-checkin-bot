#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Auto Check-in System
Telegram 自动签到系统 - 主程序
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 检查并安装依赖
def check_and_install_dependencies():
    """检查并自动安装所需依赖"""
    required_packages = {
        'python-telegram-bot': 'telegram',
        'telethon': 'telethon',
        'apscheduler': 'apscheduler',
        'pytz': 'pytz',
        'python-dotenv': 'dotenv'
    }
    
    print("检查系统依赖...")
    missing_packages = []
    
    for package, module_name in required_packages.items():
        try:
            __import__(module_name)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (未安装)")
            missing_packages.append(package)
    
    if missing_packages:
        print("\n正在安装缺失的依赖包...")
        for package in missing_packages:
            print(f"安装 {package}...")
            os.system(f"{sys.executable} -m pip install {package}")
        print("\n依赖安装完成！请重新运行程序。")
        sys.exit(0)
    else:
        print("所有依赖已就绪！\n")

# 首次运行检查依赖
check_and_install_dependencies()

# 导入模块
from bot_manager import BotManager
from user_client import UserClient
from config_manager import ConfigManager

async def main():
    """主函数"""
    print("""
╔═══════════════════════════════════════════════╗
║     Telegram Auto Check-in System v2.0        ║
║         Telegram 自动签到系统                  ║
║                                               ║
║  功能特性:                                    ║
║  • 多账号多任务签到                           ║
║  • 自定义签到命令和时间                       ║
║  • Bot交互式管理                              ║
║  • 用户权限验证                               ║
║  • 上海时区 (UTC+8)                           ║
╚═══════════════════════════════════════════════╝
    """)
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    
    # 检查是否需要初始配置
    if not config_manager.is_configured():
        await config_manager.initial_setup()
    
    # 创建用户客户端
    user_client = UserClient(config_manager)
    
    # 创建Bot管理器
    bot_manager = BotManager(config_manager, user_client)
    
    # 启动系统
    try:
        # 启动用户客户端
        await user_client.start()
        
        # 启动Bot
        await bot_manager.start()
        
        # 保持运行
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("收到退出信号，正在关闭系统...")
    except Exception as e:
        logger.error(f"系统错误: {e}")
    finally:
        await user_client.stop()
        await bot_manager.stop()
        logger.info("系统已关闭")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n再见！")
