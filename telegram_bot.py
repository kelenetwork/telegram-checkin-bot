#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram 自动签到 Bot
轻量级多任务签到机器人
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime, time
from typing import Dict, List, Optional
import subprocess

# 检查并安装依赖
def check_and_install_dependencies():
    required_packages = ['telethon', 'python-telegram-bot']
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            print(f"正在安装依赖: {package}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])

check_and_install_dependencies()

from telethon import TelegramClient, events
from telethon.tl.types import User, Chat, Channel

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TelegramAutoBot:
    def __init__(self):
        self.config_file = 'bot_config.json'
        self.tasks_file = 'tasks.json'
        self.config = {}
        self.tasks = []
        self.client = None
        self.running_tasks = []
        
    def load_config(self):
        """加载配置文件"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.interactive_setup()
    
    def save_config(self):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def interactive_setup(self):
        """交互式配置"""
        print("🔧 Telegram Bot 配置向导")
        print("=" * 40)
        
        # API配置
        api_id = input("请输入 API ID: ").strip()
        api_hash = input("请输入 API Hash: ").strip()
        bot_token = input("请输入 Bot Token (可选，用于Bot模式): ").strip()
        
        self.config = {
            'api_id': int(api_id),
            'api_hash': api_hash,
            'bot_token': bot_token if bot_token else None,
            'session_name': 'telegram_bot',
        }
        
        self.save_config()
        print("✅ 配置保存成功!")
    
    def load_tasks(self):
        """加载任务列表"""
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                self.tasks = json.load(f)
        else:
            self.tasks = []
    
    def save_tasks(self):
        """保存任务列表"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, indent=4, ensure_ascii=False)
    
    async def add_task(self, target, message, time_str, task_type='daily'):
        """添加任务"""
        task = {
            'id': len(self.tasks) + 1,
            'target': target,
            'message': message,
            'time': time_str,
            'type': task_type,
            'enabled': True,
            'last_run': None
        }
        self.tasks.append(task)
        self.save_tasks()
        return task
    
    async def remove_task(self, task_id):
        """删除任务"""
        self.tasks = [task for task in self.tasks if task['id'] != task_id]
        self.save_tasks()
    
    async def list_tasks(self):
        """列出所有任务"""
        if not self.tasks:
            return "📋 暂无任务"
        
        result = "📋 任务列表:\n\n"
        for task in self.tasks:
            status = "✅" if task['enabled'] else "❌"
            last_run = task.get('last_run', '从未运行')
            result += f"{status} ID: {task['id']}\n"
            result += f"   目标: {task['target']}\n"
            result += f"   消息: {task['message'][:30]}...\n"
            result += f"   时间: {task['time']}\n"
            result += f"   上次运行: {last_run}\n\n"
        
        return result
    
    async def send_message(self, target, message):
        """发送消息"""
        try:
            if target.startswith('@'):
                entity = await self.client.get_entity(target)
            else:
                entity = await self.client.get_entity(int(target))
            
            await self.client.send_message(entity, message)
            logger.info(f"消息发送成功: {target}")
            return True
        except Exception as e:
            logger.error(f"消息发送失败 {target}: {e}")
            return False
    
    async def execute_task(self, task):
        """执行任务"""
        try:
            success = await self.send_message(task['target'], task['message'])
            if success:
                task['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.save_tasks()
                logger.info(f"任务 {task['id']} 执行成功")
            else:
                logger.error(f"任务 {task['id']} 执行失败")
        except Exception as e:
            logger.error(f"任务 {task['id']} 执行异常: {e}")
    
    async def schedule_task(self, task):
        """调度任务"""
        while task['enabled']:
            try:
                # 解析时间
                hour, minute = map(int, task['time'].split(':'))
                target_time = time(hour, minute)
                now = datetime.now().time()
                
                # 计算到执行时间的秒数
                target_datetime = datetime.combine(datetime.now().date(), target_time)
                if now > target_time:
                    # 如果今天的时间已过，设置为明天
                    from datetime import timedelta
                    target_datetime += timedelta(days=1)
                
                wait_seconds = (target_datetime - datetime.now()).total_seconds()
                
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                await self.execute_task(task)
                
                # 每日任务等待到第二天
                if task['type'] == 'daily':
                    await asyncio.sleep(86400)  # 24小时
                    
            except Exception as e:
                logger.error(f"调度任务 {task['id']} 异常: {e}")
                await asyncio.sleep(60)  # 出错后等待1分钟重试
    
    async def start_bot(self):
        """启动Bot"""
        self.load_config()
        self.load_tasks()
        
        # 创建客户端
        self.client = TelegramClient(
            self.config['session_name'],
            self.config['api_id'],
            self.config['api_hash']
        )
        
        await self.client.start(bot_token=self.config.get('bot_token'))
        
        # 获取用户信息
        me = await self.client.get_me()
        user_info = f"用户ID: {me.id}\n用户名: @{me.username}\n权限状态: ✅ 已连接"
        
        print("🎉 欢迎使用Telegram自动签到系统!")
        print("=" * 40)
        print(user_info)
        print("🔥 管理员")
        print("\n可用命令列表:")
        print("基础命令:")
        print("/start - 开始使用")
        print("/help - 显示帮助")
        print("\n任务管理:")
        print("/addtask - 添加签到任务")
        print("/listtasks - 查看我的任务")
        print("/edittask - 编辑任务")
        print("/deletetask - 删除任务")
        print("/testtask - 测试任务")
        print("\n👀 管理员专用👀")
        print("/adduser - 添加授权用户")
        print("/removeuser - 移除用户")
        print("/listusers - 查看所有用户")
        print("/status - 系统状态")
        print("/settings - 系统设置")
        
        # 启动已有任务
        for task in self.tasks:
            if task['enabled']:
                task_coroutine = self.schedule_task(task)
                self.running_tasks.append(asyncio.create_task(task_coroutine))
        
        # 处理命令
        @self.client.on(events.NewMessage(pattern='/start'))
        async def start_handler(event):
            await event.respond("🎉 欢迎使用Telegram自动签到系统!\n\n使用 /help 查看可用命令")
        
        @self.client.on(events.NewMessage(pattern='/help'))
        async def help_handler(event):
            help_text = """📖 命令帮助:

🔹 基础命令:
/start - 开始使用
/help - 显示此帮助

🔹 任务管理:
/addtask - 添加新的签到任务
/listtasks - 查看所有任务
/deletetask - 删除指定任务

🔹 使用示例:
/addtask @channel_name 签到消息 09:00

📝 支持的目标类型:
- @username (用户名)
- @channelname (频道名)
- 123456789 (数字ID)"""
            await event.respond(help_text)
        
        @self.client.on(events.NewMessage(pattern=r'/addtask'))
        async def addtask_handler(event):
            try:
                parts = event.text.split(' ', 4)
                if len(parts) < 4:
                    await event.respond("❌ 格式错误!\n正确格式: /addtask <目标> <消息> <时间>\n示例: /addtask @channel 签到 09:00")
                    return
                
                _, target, message, time_str = parts
                task = await self.add_task(target, message, time_str)
                
                # 启动新任务
                task_coroutine = self.schedule_task(task)
                self.running_tasks.append(asyncio.create_task(task_coroutine))
                
                await event.respond(f"✅ 任务添加成功!\nID: {task['id']}\n目标: {target}\n时间: {time_str}")
            except Exception as e:
                await event.respond(f"❌ 添加任务失败: {str(e)}")
        
        @self.client.on(events.NewMessage(pattern='/listtasks'))
        async def listtasks_handler(event):
            result = await self.list_tasks()
            await event.respond(result)
        
        @self.client.on(events.NewMessage(pattern=r'/deletetask (\d+)'))
        async def deletetask_handler(event):
            try:
                task_id = int(event.pattern_match.group(1))
                await self.remove_task(task_id)
                await event.respond(f"✅ 任务 {task_id} 已删除")
            except Exception as e:
                await event.respond(f"❌ 删除失败: {str(e)}")
        
        logger.info("Bot 启动成功!")
        await self.client.run_until_disconnected()

def main():
    """主函数"""
    bot = TelegramAutoBot()
    
    try:
        asyncio.run(bot.start_bot())
    except KeyboardInterrupt:
        print("\n👋 Bot 已停止")
    except Exception as e:
        logger.error(f"Bot 运行错误: {e}")

if __name__ == "__main__":
    main()
