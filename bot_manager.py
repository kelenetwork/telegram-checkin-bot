#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import pytz
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config_manager import ConfigManager
from user_client import UserClient

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BotManager:
    def __init__(self):
        self.config = ConfigManager()
        self.user_client = None
        self.application = None
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))
        self.is_running = False
        self.user_states = {}  # 用户状态管理

    async def initialize(self) -> bool:
        """初始化机器人"""
        try:
            # 检查必要配置
            bot_token = self.config.get_bot_token()
            if not bot_token:
                logger.error("❌ Bot Token 未配置")
                return False

            # 初始化Bot应用
            self.application = Application.builder().token(bot_token).build()

            # 注册处理器
            self._register_handlers()

            # 初始化用户客户端
            api_id, api_hash = self.config.get_api_credentials()
            if api_id and api_hash:
                self.user_client = UserClient(api_id, api_hash)
                await self.user_client.start()

            # 启动调度器
            self.scheduler.start()

            # 加载现有任务
            await self._load_scheduled_tasks()

            logger.info("✅ 机器人初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 机器人初始化失败: {e}")
            return False

    def _register_handlers(self):
        """注册命令处理器"""
        # 命令处理器
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("login", self.login_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("tasks", self.tasks_command))
        self.application.add_handler(CommandHandler("addtask", self.add_task_command))
        self.application.add_handler(CommandHandler("deltask", self.delete_task_command))
        self.application.add_handler(CommandHandler("runtask", self.run_task_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))

        # 管理员命令
        self.application.add_handler(CommandHandler("admin", self.admin_command))
        self.application.add_handler(CommandHandler("users", self.users_command))
        self.application.add_handler(CommandHandler("adduser", self.add_user_command))
        self.application.add_handler(CommandHandler("deluser", self.del_user_command))

        # 回调查询处理器
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        # 消息处理器
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.text_handler))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """开始命令"""
        user_id = update.effective_user.id
        
        welcome_msg = """
🤖 **Telegram 签到机器人**

欢迎使用！此机器人可以帮助您自动完成各种签到任务。

**主要功能：**
• 🔄 定时自动签到
• 📝 自定义签到消息
• ⏰ 灵活的时间设置
• 📊 详细的统计报告

**快速开始：**
1. 使用 /login 登录您的Telegram账号
2. 使用 /addtask 添加签到任务
3. 机器人将自动按计划执行

输入 /help 查看所有命令
        """

        keyboard = [
            [InlineKeyboardButton("📚 帮助", callback_data="help"),
             InlineKeyboardButton("⚙️ 设置", callback_data="settings")],
            [InlineKeyboardButton("📋 任务列表", callback_data="tasks"),
             InlineKeyboardButton("📊 统计", callback_data="stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """帮助命令"""
        help_text = """
📚 **命令帮助**

**基本命令：**
• `/start` - 开始使用机器人
• `/help` - 显示帮助信息
• `/status` - 查看连接状态

**账号管理：**
• `/login` - 登录Telegram账号

**任务管理：**
• `/tasks` - 查看任务列表
• `/addtask` - 添加新任务
• `/deltask <任务ID>` - 删除任务
• `/runtask <任务ID>` - 立即执行任务

**统计信息：**
• `/stats` - 查看统计信息

**设置：**
• `/settings` - 机器人设置

**管理员命令：**
• `/admin` - 管理员面板
• `/users` - 用户管理
• `/adduser <用户ID>` - 添加授权用户
• `/deluser <用户ID>` - 删除授权用户

**使用示例：**
/addtask
目标: @channel_name
消息: 签到打卡 ✅
时间: 09:00
                """
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def login_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """登录命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        if not self.user_client:
            await update.message.reply_text("❌ 用户客户端未配置，请联系管理员")
            return

        if self.user_client.is_connected:
            user_info = await self.user_client.get_me()
            if user_info:
                msg = f"✅ 已登录账号：@{user_info.get('username', 'N/A')}"
                keyboard = [[InlineKeyboardButton("🚪 登出", callback_data="logout")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(msg, reply_markup=reply_markup)
            return

        # 开始登录流程
        self.user_states[user_id] = {"state": "waiting_phone"}
        await update.message.reply_text(
            "📱 请发送您的手机号码（包含国家代码）\n"
            "例如：+8613800138000\n\n"
            "发送 /cancel 取消登录"
        )
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """状态命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        # 检查用户客户端状态
        user_status = "❌ 未连接"
        user_info = None
        
        if self.user_client and self.user_client.is_connected:
            if await self.user_client.check_connection():
                user_status = "✅ 已连接"
                user_info = await self.user_client.get_me()
            else:
                user_status = "⚠️ 连接异常"

        # 获取任务统计
        user_tasks = self.config.get_user_tasks(user_id)
        enabled_tasks = len([t for t in user_tasks if t.get("enabled", True)])
        
        # 构建状态消息
        status_msg = f"""
📊 **系统状态**

**用户客户端：** {user_status}
"""
        
        if user_info:
            status_msg += f"**已登录账号：** @{user_info.get('username', 'N/A')}\n"
        
        status_msg += f"""
**任务状态：**
• 总任务数：{len(user_tasks)}
• 已启用：{enabled_tasks}
• 已禁用：{len(user_tasks) - enabled_tasks}

**调度器：** {'✅ 运行中' if self.scheduler.running else '❌ 已停止'}
"""

        keyboard = [
            [InlineKeyboardButton("🔄 刷新", callback_data="refresh_status")],
            [InlineKeyboardButton("📋 任务列表", callback_data="tasks")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(status_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def tasks_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """任务列表命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        tasks = self.config.get_user_tasks(user_id)
        
        if not tasks:
            keyboard = [[InlineKeyboardButton("➕ 添加任务", callback_data="add_task")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "📋 您还没有任何任务\n\n点击下方按钮或使用 /addtask 添加任务",
                reply_markup=reply_markup
            )
            return

        # 构建任务列表
        tasks_msg = "📋 **您的任务列表：**\n\n"
        
        for task in tasks:
            status = "✅" if task.get("enabled", True) else "❌"
            task_type = task.get("type", "unknown")
            target = task.get("target", "未知")
            schedule = task.get("schedule", {})
            
            # 格式化时间显示
            time_str = ""
            if task_type == "daily":
                time_str = schedule.get("time", "未设置")
            elif task_type == "interval":
                time_str = f"每{schedule.get('minutes', 0)}分钟"
            elif task_type == "cron":
                time_str = schedule.get("expression", "未设置")

            # 统计信息
            run_count = task.get("run_count", 0)
            success_count = task.get("success_count", 0)
            success_rate = (success_count / run_count * 100) if run_count > 0 else 0

            tasks_msg += f"""
**任务 #{task['id']}** {status}
📍 目标：{target}
⏰ 时间：{time_str}
📊 执行：{run_count}次 (成功率: {success_rate:.1f}%)
"""

        # 添加操作按钮
        keyboard = []
        # 每行最多3个任务按钮
        for i in range(0, len(tasks), 3):
            row = []
            for j in range(3):
                if i + j < len(tasks):
                    task = tasks[i + j]
                    status_emoji = "✅" if task.get("enabled", True) else "❌"
                    row.append(InlineKeyboardButton(
                        f"{status_emoji} #{task['id']}",
                        callback_data=f"task_{task['id']}"
                    ))
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("➕ 添加任务", callback_data="add_task"),
            InlineKeyboardButton("🔄 刷新", callback_data="refresh_tasks")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(tasks_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def add_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加任务命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        if not self.user_client or not self.user_client.is_connected:
            await update.message.reply_text("❌ 请先使用 /login 登录账号")
            return

        # 检查任务数量限制
        current_tasks = len(self.config.get_user_tasks(user_id))
        max_tasks = self.config.get_setting("max_tasks_per_user", 10)
        
        if current_tasks >= max_tasks:
            await update.message.reply_text(f"❌ 任务数量已达上限 ({max_tasks})")
            return

        # 开始添加任务流程
        self.user_states[user_id] = {
            "state": "adding_task",
            "step": "target",
            "task_data": {}
        }
        
        keyboard = [[InlineKeyboardButton("❌ 取消", callback_data="cancel_add_task")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📝 **添加新任务**\n\n"
            "第1步：请输入目标\n"
            "支持格式：\n"
            "• @用户名\n"
            "• @频道名\n"
            "• 群组ID\n"
            "• https://t.me/xxx\n\n"
            "请输入目标：",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def delete_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除任务命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        if not context.args:
            await update.message.reply_text("❌ 请指定任务ID\n使用方法：/deltask <任务ID>")
            return

        try:
            task_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ 任务ID必须是数字")
            return

        # 删除任务
        if self.config.delete_task(user_id, task_id):
            # 移除调度任务
            job_id = f"task_{user_id}_{task_id}"
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            await update.message.reply_text(f"✅ 任务 #{task_id} 已删除")
        else:
            await update.message.reply_text(f"❌ 任务 #{task_id} 不存在")

    async def run_task_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """立即执行任务命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        if not context.args:
            await update.message.reply_text("❌ 请指定任务ID\n使用方法：/runtask <任务ID>")
            return

        try:
            task_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ 任务ID必须是数字")
            return

        task = self.config.get_task(user_id, task_id)
        if not task:
            await update.message.reply_text(f"❌ 任务 #{task_id} 不存在")
            return

        await update.message.reply_text(f"🚀 正在执行任务 #{task_id}...")
        
        # 执行任务
        success = await self._execute_task(task)
        
        if success:
            await update.message.reply_text(f"✅ 任务 #{task_id} 执行成功")
        else:
            await update.message.reply_text(f"❌ 任务 #{task_id} 执行失败")

    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """统计命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        # 获取用户任务统计
        user_tasks = self.config.get_user_tasks(user_id)
        
        total_runs = sum(task.get("run_count", 0) for task in user_tasks)
        total_success = sum(task.get("success_count", 0) for task in user_tasks)
        success_rate = (total_success / total_runs * 100) if total_runs > 0 else 0
        
        # 获取今日统计
        today = datetime.now(pytz.timezone('Asia/Shanghai')).date()
        today_runs = 0
        today_success = 0
        
        for task in user_tasks:
            last_run = task.get("last_run")
            if last_run:
                last_run_date = datetime.fromtimestamp(last_run, pytz.timezone('Asia/Shanghai')).date()
                if last_run_date == today:
                    today_runs += 1
                    if task.get("success_count", 0) > task.get("error_count", 0):
                        today_success += 1

        stats_msg = f"""
📊 **个人统计**

**任务概况：**
• 总任务数：{len(user_tasks)}
• 启用任务：{len([t for t in user_tasks if t.get("enabled", True)])}
• 禁用任务：{len([t for t in user_tasks if not t.get("enabled", True)])}

**执行统计：**
• 总执行次数：{total_runs}
• 成功次数：{total_success}
• 失败次数：{total_runs - total_success}
• 成功率：{success_rate:.1f}%

**今日统计：**
• 今日执行：{today_runs}次
• 今日成功：{today_success}次
"""

        # 管理员可查看系统统计
        if self.config.is_admin_user(user_id):
            system_stats = self.config.get_stats()
            stats_msg += f"""

📈 **系统统计**
• 总用户数：{system_stats['total_users']}
• 管理员数：{system_stats['admin_users']}
• 系统任务数：{system_stats['total_tasks']}
• 系统成功率：{system_stats['success_rate']}%
"""

        keyboard = [[InlineKeyboardButton("🔄 刷新", callback_data="refresh_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(stats_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """设置命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_authorized_user(user_id):
            await update.message.reply_text("❌ 您没有权限使用此功能")
            return

        settings_msg = """
⚙️ **机器人设置**

当前设置：
"""
        
        timezone = self.config.get_timezone()
        settings_msg += f"🌏 时区：{timezone}\n"
        
        keyboard = [
            [InlineKeyboardButton("🌏 时区设置", callback_data="setting_timezone")],
            [InlineKeyboardButton("🔄 刷新", callback_data="refresh_settings")]
        ]
        
        # 管理员设置
        if self.config.is_admin_user(user_id):
            keyboard.insert(-1, [InlineKeyboardButton("👑 管理员设置", callback_data="admin_settings")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(settings_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """管理员命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_admin_user(user_id):
            await update.message.reply_text("❌ 您没有管理员权限")
            return

        system_stats = self.config.get_stats()
        admin_msg = f"""
👑 **管理员面板**

**系统概览：**
• 授权用户：{system_stats['total_users']}
• 管理员：{system_stats['admin_users']}
• 系统任务：{system_stats['total_tasks']}
• 运行任务：{system_stats['enabled_tasks']}
• 系统成功率：{system_stats['success_rate']}%

**系统状态：**
• 调度器：{'✅ 运行中' if self.scheduler.running else '❌ 已停止'}
• 用户客户端：{'✅ 已连接' if self.user_client and self.user_client.is_connected else '❌ 未连接'}
"""

        keyboard = [
            [InlineKeyboardButton("👥 用户管理", callback_data="admin_users"),
             InlineKeyboardButton("📋 任务管理", callback_data="admin_tasks")],
            [InlineKeyboardButton("⚙️ 系统设置", callback_data="admin_settings"),
             InlineKeyboardButton("📊 详细统计", callback_data="admin_stats")],
            [InlineKeyboardButton("🔄 刷新", callback_data="refresh_admin")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(admin_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """用户管理命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_admin_user(user_id):
            await update.message.reply_text("❌ 您没有管理员权限")
            return

        authorized_users = self.config.get_authorized_users()
        admin_users = self.config.get_admin_users()
        
        users_msg = "👥 **用户管理**\n\n"
        users_msg += f"授权用户总数：{len(authorized_users)}\n"
        users_msg += f"管理员总数：{len(admin_users)}\n\n"
        
        users_msg += "**管理员列表：**\n"
        for admin_id in admin_users:
            users_msg += f"• {admin_id} 👑\n"
        
        users_msg += "\n**授权用户列表：**\n"
        for auth_id in authorized_users:
            if auth_id not in admin_users:
                users_msg += f"• {auth_id}\n"

        keyboard = [
            [InlineKeyboardButton("➕ 添加用户", callback_data="add_user"),
             InlineKeyboardButton("➖ 删除用户", callback_data="del_user")],
            [InlineKeyboardButton("🔄 刷新", callback_data="refresh_users")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(users_msg, reply_markup=reply_markup, parse_mode='Markdown')

    async def add_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """添加用户命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_admin_user(user_id):
            await update.message.reply_text("❌ 您没有管理员权限")
            return

        if not context.args:
            await update.message.reply_text("❌ 请指定用户ID\n使用方法：/adduser <用户ID>")
            return

        try:
            new_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ 用户ID必须是数字")
            return

        if self.config.add_authorized_user(new_user_id):
            await update.message.reply_text(f"✅ 用户 {new_user_id} 已添加到授权列表")
        else:
            await update.message.reply_text(f"ℹ️ 用户 {new_user_id} 已在授权列表中")

    async def del_user_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """删除用户命令"""
        user_id = update.effective_user.id
        
        if not self.config.is_admin_user(user_id):
            await update.message.reply_text("❌ 您没有管理员权限")
            return

        if not context.args:
            await update.message.reply_text("❌ 请指定用户ID\n使用方法：/deluser <用户ID>")
            return

        try:
            del_user_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ 用户ID必须是数字")
            return

        if del_user_id in self.config.get_admin_users():
            await update.message.reply_text("❌ 不能删除管理员用户")
            return

        if self.config.remove_authorized_user(del_user_id):
            await update.message.reply_text(f"✅ 用户 {del_user_id} 已从授权列表中移除")
        else:
            await update.message.reply_text(f"ℹ️ 用户 {del_user_id} 不在授权列表中")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理按钮回调"""
        query = update.callback_query
        await query.answer()
        
        user_id = query.from_user.id
        data = query.data

        # 权限检查
        if not self.config.is_authorized_user(user_id) and not data.startswith("help"):
            await query.edit_message_text("❌ 您没有权限使用此功能")
            return

        try:
            if data == "help":
                await self.help_command(update, context)
            elif data == "settings":
                await self.settings_command(update, context)
            elif data == "tasks":
                await self.tasks_command(update, context)
            elif data == "stats":
                await self.stats_command(update, context)
            elif data == "add_task":
                await self.add_task_command(update, context)
            elif data.startswith("task_"):
                await self._handle_task_details(query, data)
            elif data == "refresh_status":
                await self.status_command(update, context)
            elif data == "refresh_tasks":
                await self.tasks_command(update, context)
            elif data == "refresh_stats":
                await self.stats_command(update, context)
            elif data == "refresh_settings":
                await self.settings_command(update, context)
            elif data == "cancel_add_task":
                await self._cancel_add_task(query)
            elif data == "logout":
                await self._handle_logout(query)
            # 管理员回调
            elif data.startswith("admin_") and self.config.is_admin_user(user_id):
                await self._handle_admin_callback(query, data)
            else:
                await query.edit_message_text("❌ 未知的操作")
                
        except Exception as e:
            logger.error(f"❌ 处理回调失败: {e}")
            await query.edit_message_text("❌ 处理请求时出错，请重试")

    async def text_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理文本消息"""
        user_id = update.effective_user.id
        text = update.message.text

        if user_id not in self.user_states:
            return

        state_info = self.user_states[user_id]
        state = state_info.get("state")

        try:
            if state == "waiting_phone":
                await self._handle_phone_input(update, text)
            elif state == "waiting_code":
                await self._handle_code_input(update, text)
            elif state == "waiting_password":
                await self._handle_password_input(update, text)
            elif state == "adding_task":
                await self._handle_add_task_input(update, text)
        except Exception as e:
            logger.error(f"❌ 处理文本消息失败: {e}")
            await update.message.reply_text("❌ 处理消息时出错，请重试")

    async def _handle_phone_input(self, update: Update, phone: str):
        """处理手机号输入"""
        user_id = update.effective_user.id
        
        if phone == "/cancel":
            del self.user_states[user_id]
            await update.message.reply_text("❌ 登录已取消")
            return

        # 验证手机号格式
        if not phone.startswith('+') or len(phone) < 10:
            await update.message.reply_text("❌ 手机号格式错误，请重新输入")
            return

        # 发送验证码
        result = await self.user_client.login_with_phone(phone)
        
        if result["success"]:
            self.user_states[user_id] = {
                "state": "waiting_code",
                "phone": phone,
                "phone_code_hash": result.get("phone_code_hash")
            }
            await update.message.reply_text(
                "✅ 验证码已发送到您的手机\n"
                "请输入收到的验证码："
            )
        else:
            await update.message.reply_text(f"❌ 发送验证码失败：{result['error']}")

    async def _handle_code_input(self, update: Update, code: str):
        """处理验证码输入"""
        user_id = update.effective_user.id
        state_info = self.user_states[user_id]
        phone = state_info["phone"]

        if code == "/cancel":
            del self.user_states[user_id]
            await update.message.reply_text("❌ 登录已取消")
            return

        # 验证登录码
        result = await self.user_client.verify_code(phone, code)
        
        if result["success"]:
            del self.user_states[user_id]
            user_info = result["user"]
            await update.message.reply_text(
                f"✅ 登录成功！\n"
                f"账号：@{user_info.get('username', 'N/A')}\n"
                f"姓名：{user_info.get('first_name', 'N/A')}"
            )
        elif result.get("need_password"):
            self.user_states[user_id]["state"] = "waiting_password"
            await update.message.reply_text("🔐 请输入两步验证密码：")
        else:
            await update.message.reply_text(f"❌ 验证失败：{result['error']}")

    async def _handle_password_input(self, update: Update, password: str):
        """处理密码输入"""
        user_id = update.effective_user.id
        state_info = self.user_states[user_id]
        phone = state_info["phone"]

        if password == "/cancel":
            del self.user_states[user_id]
            await update.message.reply_text("❌ 登录已取消")
            return

        # 使用密码完成登录
        result = await self.user_client.verify_code(phone, "", password)
        
        if result["success"]:
            del self.user_states[user_id]
            user_info = result["user"]
            await update.message.reply_text(
                f"✅ 登录成功！\n"
                f"账号：@{user_info.get('username', 'N/A')}\n"
                f"姓名：{user_info.get('first_name', 'N/A')}"
            )
        else:
            await update.message.reply_text(f"❌ 登录失败：{result['error']}")

    async def _handle_add_task_input(self, update: Update, text: str):
        """处理添加任务的输入"""
        user_id = update.effective_user.id
        state_info = self.user_states[user_id]
        step = state_info["step"]
        task_data = state_info["task_data"]

        if text == "/cancel":
            del self.user_states[user_id]
            await update.message.reply_text("❌ 添加任务已取消")
            return

        if step == "target":
            # 验证目标有效性
            if not await self._validate_target(text):
                await update.message.reply_text("❌ 目标格式错误或无效，请重新输入")
                return
            
            task_data["target"] = text
            state_info["step"] = "message"
            
            await update.message.reply_text(
                "📝 第2步：请输入要发送的消息内容\n\n"
                "支持emoji和换行，例如：\n"
                "签到打卡 ✅\n"
                "今日任务完成！"
            )
            
        elif step == "message":
            task_data["message"] = text
            state_info["step"] = "schedule_type"
            
            keyboard = [
                [InlineKeyboardButton("📅 每日定时", callback_data="schedule_daily")],
                [InlineKeyboardButton("⏱️ 间隔执行", callback_data="schedule_interval")],
                [InlineKeyboardButton("🔧 自定义Cron", callback_data="schedule_cron")],
                [InlineKeyboardButton("❌ 取消", callback_data="cancel_add_task")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "⏰ 第3步：选择执行时间类型",
                reply_markup=reply_markup
            )
            
        elif step == "daily_time":
            # 验证时间格式
            if not self._validate_time_format(text):
                await update.message.reply_text("❌ 时间格式错误，请输入 HH:MM 格式（如：09:30）")
                return
                
            hour, minute = map(int, text.split(':'))
            task_data["schedule"] = {
                "type": "daily",
                "hour": hour,
                "minute": minute,
                "time": text
            }
            
            await self._finish_add_task(update, user_id, task_data)
            
        elif step == "interval_minutes":
            try:
                minutes = int(text)
                if minutes < 1 or minutes > 1440:  # 最多24小时
                    await update.message.reply_text("❌ 间隔时间必须在1-1440分钟之间")
                    return
            except ValueError:
                await update.message.reply_text("❌ 请输入有效的数字")
                return
                
            task_data["schedule"] = {
                "type": "interval",
                "minutes": minutes
            }
            
            await self._finish_add_task(update, user_id, task_data)
            
        elif step == "cron_expression":
            if not self._validate_cron_expression(text):
                await update.message.reply_text("❌ Cron表达式格式错误")
                return
                
            task_data["schedule"] = {
                "type": "cron",
                "expression": text
            }
            
            await self._finish_add_task(update, user_id, task_data)

        async def _validate_target(self, target: str) -> bool:
        """验证目标有效性"""
        try:
            if not self.user_client or not self.user_client.is_connected:
                return False
                
            entity = await self.user_client.resolve_entity(target)
            return entity is not None
        except Exception as e:
            logger.error(f"❌ 验证目标失败: {e}")
            return False

    def _validate_time_format(self, time_str: str) -> bool:
        """验证时间格式"""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            
            hour, minute = map(int, parts)
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except ValueError:
            return False

    def _validate_cron_expression(self, cron_expr: str) -> bool:
        """验证Cron表达式"""
        try:
            # 简单的Cron表达式验证
            parts = cron_expr.split()
            if len(parts) != 5:
                return False
            return True
        except Exception:
            return False

    async def _finish_add_task(self, update: Update, user_id: int, task_data: Dict):
        """完成任务添加"""
        try:
            # 生成任务ID
            task_id = self.config.generate_task_id()
            
            # 构建完整任务数据
            task = {
                "id": task_id,
                "user_id": user_id,
                "target": task_data["target"],
                "message": task_data["message"],
                "schedule": task_data["schedule"],
                "enabled": True,
                "created_at": datetime.now(pytz.timezone('Asia/Shanghai')).timestamp(),
                "run_count": 0,
                "success_count": 0,
                "error_count": 0,
                "last_run": None,
                "last_error": None
            }
            
            # 保存任务
            if self.config.add_task(user_id, task):
                # 创建调度任务
                await self._schedule_task(task)
                
                # 清理状态
                del self.user_states[user_id]
                
                # 发送成功消息
                schedule_info = task_data["schedule"]
                schedule_text = ""
                if schedule_info["type"] == "daily":
                    schedule_text = f"每日 {schedule_info['time']}"
                elif schedule_info["type"] == "interval":
                    schedule_text = f"每 {schedule_info['minutes']} 分钟"
                elif schedule_info["type"] == "cron":
                    schedule_text = f"Cron: {schedule_info['expression']}"
                
                success_msg = f"""
✅ **任务添加成功！**

**任务详情：**
• 任务ID：#{task_id}
• 目标：{task_data["target"]}
• 消息：{task_data["message"]}
• 执行时间：{schedule_text}

任务将自动按计划执行。
"""
                
                keyboard = [
                    [InlineKeyboardButton("📋 查看任务", callback_data="tasks")],
                    [InlineKeyboardButton("🚀 立即执行", callback_data=f"run_task_{task_id}")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(success_msg, reply_markup=reply_markup, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ 保存任务失败，请重试")
                
        except Exception as e:
            logger.error(f"❌ 完成任务添加失败: {e}")
            await update.message.reply_text("❌ 添加任务时出错，请重试")

    async def _schedule_task(self, task: Dict):
        """调度任务"""
        try:
            job_id = f"task_{task['user_id']}_{task['id']}"
            schedule = task["schedule"]
            
            # 移除已存在的任务
            if self.scheduler.get_job(job_id):
                self.scheduler.remove_job(job_id)
            
            # 根据调度类型创建任务
            if schedule["type"] == "daily":
                trigger = CronTrigger(
                    hour=schedule["hour"],
                    minute=schedule["minute"],
                    timezone="Asia/Shanghai"
                )
                
            elif schedule["type"] == "interval":
                trigger = IntervalTrigger(
                    minutes=schedule["minutes"],
                    timezone="Asia/Shanghai"
                )
                
            elif schedule["type"] == "cron":
                trigger = CronTrigger.from_crontab(
                    schedule["expression"],
                    timezone="Asia/Shanghai"
                )
            else:
                logger.error(f"❌ 未知的调度类型: {schedule['type']}")
                return False
                
            # 添加调度任务
            self.scheduler.add_job(
                func=self._execute_task_wrapper,
                trigger=trigger,
                id=job_id,
                args=[task],
                replace_existing=True
            )
            
            logger.info(f"✅ 任务 #{task['id']} 已调度")
            return True
            
        except Exception as e:
            logger.error(f"❌ 调度任务失败: {e}")
            return False

    async def _execute_task_wrapper(self, task: Dict):
        """任务执行包装器"""
        try:
            success = await self._execute_task(task)
            
            # 更新任务统计
            task["run_count"] = task.get("run_count", 0) + 1
            task["last_run"] = datetime.now(pytz.timezone('Asia/Shanghai')).timestamp()
            
            if success:
                task["success_count"] = task.get("success_count", 0) + 1
                task["last_error"] = None
            else:
                task["error_count"] = task.get("error_count", 0) + 1
                
            # 保存任务更新
            self.config.update_task(task["user_id"], task["id"], task)
            
        except Exception as e:
            logger.error(f"❌ 任务执行包装器失败: {e}")

    async def _execute_task(self, task: Dict) -> bool:
        """执行具体任务"""
        try:
            if not self.user_client or not self.user_client.is_connected:
                logger.error("❌ 用户客户端未连接")
                return False
                
            target = task["target"]
            message = task["message"]
            
            # 添加随机延迟，避免被检测
            delay = random.uniform(1, 5)
            await asyncio.sleep(delay)
            
            # 发送消息
            result = await self.user_client.send_message(target, message)
            
            if result["success"]:
                logger.info(f"✅ 任务 #{task['id']} 执行成功")
                return True
            else:
                logger.error(f"❌ 任务 #{task['id']} 执行失败: {result['error']}")
                task["last_error"] = result["error"]
                return False
                
        except Exception as e:
            logger.error(f"❌ 执行任务 #{task['id']} 失败: {e}")
            task["last_error"] = str(e)
            return False

    async def _handle_task_details(self, query, data: str):
        """处理任务详情"""
        try:
            task_id = int(data.split('_')[1])
            user_id = query.from_user.id
            
            task = self.config.get_task(user_id, task_id)
            if not task:
                await query.edit_message_text("❌ 任务不存在")
                return
                
            # 构建任务详情
            status = "✅ 启用" if task.get("enabled", True) else "❌ 禁用"
            schedule = task.get("schedule", {})
            
            schedule_text = ""
            if schedule.get("type") == "daily":
                schedule_text = f"每日 {schedule.get('time', '未设置')}"
            elif schedule.get("type") == "interval":
                schedule_text = f"每 {schedule.get('minutes', 0)} 分钟"
            elif schedule.get("type") == "cron":
                schedule_text = f"Cron: {schedule.get('expression', '未设置')}"
                
            # 统计信息
            run_count = task.get("run_count", 0)
            success_count = task.get("success_count", 0)
            error_count = task.get("error_count", 0)
            success_rate = (success_count / run_count * 100) if run_count > 0 else 0
            
            # 最后执行时间
            last_run = task.get("last_run")
            last_run_text = "从未执行"
            if last_run:
                last_run_dt = datetime.fromtimestamp(last_run, pytz.timezone('Asia/Shanghai'))
                last_run_text = last_run_dt.strftime("%Y-%m-%d %H:%M:%S")
            
            details_msg = f"""
📋 **任务详情 #{task_id}**

**基本信息：**
• 状态：{status}
• 目标：{task['target']}
• 消息：{task['message']}
• 执行时间：{schedule_text}

**统计信息：**
• 总执行：{run_count} 次
• 成功：{success_count} 次
• 失败：{error_count} 次
• 成功率：{success_rate:.1f}%
• 最后执行：{last_run_text}
"""
            
            # 如果有错误信息
            last_error = task.get("last_error")
            if last_error:
                details_msg += f"\n**最后错误：**\n{last_error}"
                
            # 构建操作按钮
            keyboard = []
            
            # 启用/禁用按钮
            toggle_text = "❌ 禁用" if task.get("enabled", True) else "✅ 启用"
            keyboard.append([InlineKeyboardButton(toggle_text, callback_data=f"toggle_task_{task_id}")])
            
            # 操作按钮
            keyboard.append([
                InlineKeyboardButton("🚀 立即执行", callback_data=f"run_task_{task_id}"),
                InlineKeyboardButton("✏️ 编辑", callback_data=f"edit_task_{task_id}")
            ])
            
            keyboard.append([
                InlineKeyboardButton("🗑️ 删除", callback_data=f"delete_task_{task_id}"),
                InlineKeyboardButton("🔙 返回", callback_data="tasks")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(details_msg, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ 处理任务详情失败: {e}")
            await query.edit_message_text("❌ 获取任务详情失败")

    async def _handle_logout(self, query):
        """处理登出"""
        try:
            if self.user_client:
                await self.user_client.disconnect()
                
            await query.edit_message_text("✅ 已登出账号")
            
        except Exception as e:
            logger.error(f"❌ 登出失败: {e}")
            await query.edit_message_text("❌ 登出时出错")

    async def _cancel_add_task(self, query):
        """取消添加任务"""
        user_id = query.from_user.id
        if user_id in self.user_states:
            del self.user_states[user_id]
        await query.edit_message_text("❌ 添加任务已取消")

    async def _handle_admin_callback(self, query, data: str):
        """处理管理员回调"""
        try:
            if data == "admin_users":
                await self.users_command(query, None)
            elif data == "admin_tasks":
                await self._show_admin_tasks(query)
            elif data == "admin_settings":
                await self._show_admin_settings(query)
            elif data == "admin_stats":
                await self._show_admin_stats(query)
            elif data == "refresh_admin":
                await self.admin_command(query, None)
            elif data == "refresh_users":
                await self.users_command(query, None)
            # 其他管理员操作...
                
        except Exception as e:
            logger.error(f"❌ 处理管理员回调失败: {e}")
            await query.edit_message_text("❌ 处理管理员操作失败")

    async def _load_scheduled_tasks(self):
        """加载已有的调度任务"""
        try:
            all_tasks = self.config.get_all_tasks()
            for task in all_tasks:
                if task.get("enabled", True):
                    await self._schedule_task(task)
                    
            logger.info(f"✅ 加载了 {len(all_tasks)} 个调度任务")
            
        except Exception as e:
            logger.error(f"❌ 加载调度任务失败: {e}")

    async def start_bot(self):
        """启动机器人"""
        try:
            if not await self.initialize():
                return False
                
            # 设置机器人命令菜单
            commands = [
                BotCommand("start", "开始使用机器人"),
                BotCommand("help", "查看帮助信息"),
                BotCommand("login", "登录Telegram账号"),
                BotCommand("status", "查看状态"),
                BotCommand("tasks", "任务列表"),
                BotCommand("addtask", "添加新任务"),
                BotCommand("stats", "统计信息"),
                BotCommand("settings", "机器人设置")
            ]
            
            await self.application.bot.set_my_commands(commands)
            
            # 启动应用
            await self.application.initialize()
            await self.application.start()
            await self.application.updater.start_polling()
            
            self.is_running = True
            logger.info("✅ 机器人启动成功")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动机器人失败: {e}")
            return False

    async def stop_bot(self):
        """停止机器人"""
        try:
            self.is_running = False
            
            # 停止调度器
            if self.scheduler.running:
                self.scheduler.shutdown()
                
                        # 停止Telegram Bot
            if self.application:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
            logger.info("✅ 机器人已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止机器人失败: {e}")

    def run(self):
        """运行机器人"""
        try:
            asyncio.run(self.start_bot())
            
            # 保持运行
            while self.is_running:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("🛑 收到中断信号，正在停止...")
            asyncio.run(self.stop_bot())
        except Exception as e:
            logger.error(f"❌ 运行机器人失败: {e}")
            asyncio.run(self.stop_bot())

    async def _show_admin_tasks(self, query):
        """显示管理员任务管理"""
        try:
            all_tasks = self.config.get_all_tasks()
            total_tasks = len(all_tasks)
            enabled_tasks = len([t for t in all_tasks if t.get("enabled", True)])
            
            tasks_msg = f"""
📋 **任务管理**

**统计信息：**
• 总任务数：{total_tasks}
• 启用任务：{enabled_tasks}
• 禁用任务：{total_tasks - enabled_tasks}

**用户任务分布：**
"""
            
            # 统计每个用户的任务数
            user_task_count = {}
            for task in all_tasks:
                user_id = task["user_id"]
                user_task_count[user_id] = user_task_count.get(user_id, 0) + 1
                
            for user_id, count in user_task_count.items():
                tasks_msg += f"• 用户 {user_id}：{count} 个任务\n"
                
            keyboard = [
                [InlineKeyboardButton("🔄 刷新", callback_data="admin_tasks")],
                [InlineKeyboardButton("🔙 返回", callback_data="refresh_admin")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(tasks_msg, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ 显示管理员任务失败: {e}")
            await query.edit_message_text("❌ 获取任务信息失败")

    async def _show_admin_settings(self, query):
        """显示管理员设置"""
        try:
            settings = self.config.get_all_settings()
            
            settings_msg = """
⚙️ **系统设置**

**当前配置：**
"""
            
            for key, value in settings.items():
                settings_msg += f"• {key}：{value}\n"
                
            keyboard = [
                [InlineKeyboardButton("🌏 时区设置", callback_data="admin_set_timezone")],
                [InlineKeyboardButton("👥 用户限制", callback_data="admin_set_limits")],
                [InlineKeyboardButton("🔄 刷新", callback_data="admin_settings")],
                [InlineKeyboardButton("🔙 返回", callback_data="refresh_admin")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(settings_msg, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ 显示管理员设置失败: {e}")
            await query.edit_message_text("❌ 获取设置信息失败")

    async def _show_admin_stats(self, query):
        """显示管理员详细统计"""
        try:
            stats = self.config.get_detailed_stats()
            
            stats_msg = f"""
📊 **详细统计**

**用户统计：**
• 总用户数：{stats['total_users']}
• 活跃用户：{stats['active_users']}
• 管理员：{stats['admin_users']}

**任务统计：**
• 总任务数：{stats['total_tasks']}
• 启用任务：{stats['enabled_tasks']}
• 今日执行：{stats['today_runs']}
• 成功率：{stats['success_rate']}%

**系统资源：**
• 调度器状态：{'运行中' if self.scheduler.running else '已停止'}
• 活动作业：{len(self.scheduler.get_jobs())}
• 用户客户端：{'已连接' if self.user_client and self.user_client.is_connected else '未连接'}
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 刷新", callback_data="admin_stats")],
                [InlineKeyboardButton("🔙 返回", callback_data="refresh_admin")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(stats_msg, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"❌ 显示管理员统计失败: {e}")
            await query.edit_message_text("❌ 获取统计信息失败")

    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'is_running') and self.is_running:
                asyncio.run(self.stop_bot())
        except Exception:
            pass


if __name__ == "__main__":
    # 创建机器人实例
    bot_manager = BotManager()
    
    # 运行机器人
    bot_manager.run()

                


