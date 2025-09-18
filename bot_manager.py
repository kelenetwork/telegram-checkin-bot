# -*- coding: utf-8 -*-
"""
Bot管理器
处理所有Bot交互和命令
"""

import uuid
import pytz
from datetime import datetime, time
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    CallbackQueryHandler, ConversationHandler, filters
)

# 会话状态
ADD_TASK_TYPE, ADD_TASK_TARGET, ADD_TASK_COMMAND, ADD_TASK_TIME = range(4)
EDIT_TASK_FIELD, EDIT_TASK_VALUE = range(2)
ADD_USER_ID = 0

class BotManager:
    def __init__(self, config_manager, user_client):
        self.config_manager = config_manager
        self.user_client = user_client
        self.app = None
        self.shanghai_tz = pytz.timezone('Asia/Shanghai')
        
        # 临时存储
        self.temp_data = {}
    
    def check_permission(self, func):
        """权限检查装饰器"""
        async def wrapper(update: Update, context):
            user_id = update.effective_user.id
            
            if not self.config_manager.is_authorized_user(user_id):
                await update.message.reply_text(
                    "❌ 您没有使用权限！\n"
                    "请联系管理员授权。"
                )
                return
            
            return await func(update, context)
        return wrapper
    
    def admin_only(self, func):
        """管理员权限装饰器"""
        async def wrapper(update: Update, context):
            user_id = update.effective_user.id
            
            if not self.config_manager.is_admin_user(user_id):
                await update.message.reply_text("❌ 此功能仅管理员可用！")
                return
            
            return await func(update, context)
        return wrapper
    
    async def start(self):
        """启动Bot"""
        self.app = Application.builder().token(
            self.config_manager.config['bot_token']
        ).build()
        
        # 基础命令
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        
        # 任务管理命令（需要权限）
        self.app.add_handler(CommandHandler("add_task", self.check_permission(self.cmd_add_task)))
        self.app.add_handler(CommandHandler("list_tasks", self.check_permission(self.cmd_list_tasks)))
        self.app.add_handler(CommandHandler("edit_task", self.check_permission(self.cmd_edit_task)))
        self.app.add_handler(CommandHandler("delete_task", self.check_permission(self.cmd_delete_task)))
        self.app.add_handler(CommandHandler("test_task", self.check_permission(self.cmd_test_task)))
        
        # 用户管理命令（仅管理员）
        self.app.add_handler(CommandHandler("add_user", self.admin_only(self.cmd_add_user)))
        self.app.add_handler(CommandHandler("remove_user", self.admin_only(self.cmd_remove_user)))
        self.app.add_handler(CommandHandler("list_users", self.admin_only(self.cmd_list_users)))
        
        # 系统命令（仅管理员）
        self.app.add_handler(CommandHandler("status", self.admin_only(self.cmd_status)))
        self.app.add_handler(CommandHandler("settings", self.admin_only(self.cmd_settings)))
        
        # 会话处理器 - 添加任务
        add_task_handler = ConversationHandler(
            entry_points=[CommandHandler("add_task", self.check_permission(self.cmd_add_task))],
            states={
                ADD_TASK_TYPE: [CallbackQueryHandler(self.add_task_type)],
                ADD_TASK_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_task_target)],
                ADD_TASK_COMMAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_task_command)],
                ADD_TASK_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_task_time)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(add_task_handler)
        # 添加用户会话处理器
        add_user_handler = ConversationHandler(
            entry_points=[CommandHandler("add_user", self.admin_only(self.cmd_add_user))],
            states={
                ADD_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_user_process)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.app.add_handler(add_user_handler)
        
        # 回调查询处理器
        self.app.add_handler(CallbackQueryHandler(self.button_callback))
        
        # 启动Bot
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
    
    async def stop(self):
        """停止Bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
    
    async def cmd_start(self, update: Update, context):
        """开始命令"""
        user = update.effective_user
        is_authorized = self.config_manager.is_authorized_user(user.id)
        is_admin = self.config_manager.is_admin_user(user.id)
        
        welcome_text = f"""
👋 欢迎使用 Telegram 自动签到系统！

用户ID: `{user.id}`
用户名: @{user.username or '未设置'}
权限状态: {'✅ 已授权' if is_authorized else '❌ 未授权'}
{'👑 管理员' if is_admin else ''}

使用 /help 查看可用命令
        """
        
        await update.message.reply_text(
            welcome_text,
            parse_mode='Markdown'
        )
    
    async def cmd_help(self, update: Update, context):
        """帮助命令"""
        user_id = update.effective_user.id
        is_authorized = self.config_manager.is_authorized_user(user_id)
        is_admin = self.config_manager.is_admin_user(user_id)
        
        help_text = "📚 **可用命令列表**\n\n"
        
        # 基础命令
        help_text += "**基础命令:**\n"
        help_text += "/start - 开始使用\n"
        help_text += "/help - 显示帮助\n"
        
        if is_authorized:
            # 任务管理
            help_text += "\n**任务管理:**\n"
            help_text += "/add_task - 添加签到任务\n"
            help_text += "/list_tasks - 查看我的任务\n"
            help_text += "/edit_task - 编辑任务\n"
            help_text += "/delete_task - 删除任务\n"
            help_text += "/test_task - 测试签到\n"
        
        if is_admin:
            # 管理员命令
            help_text += "\n**管理员命令:**\n"
            help_text += "/add_user - 添加授权用户\n"
            help_text += "/remove_user - 移除用户\n"
            help_text += "/list_users - 查看所有用户\n"
            help_text += "/status - 系统状态\n"
            help_text += "/settings - 系统设置\n"
        
        if not is_authorized:
            help_text += "\n❗ 您还未获得使用权限，请联系管理员。"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_add_task(self, update: Update, context):
        """添加任务 - 开始"""
        keyboard = [
            [
                InlineKeyboardButton("👥 群组签到", callback_data="task_type_group"),
                InlineKeyboardButton("🤖 Bot签到", callback_data="task_type_bot")
            ],
            [InlineKeyboardButton("❌ 取消", callback_data="cancel")]
        ]
        
        await update.message.reply_text(
            "请选择签到类型:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        return ADD_TASK_TYPE
    
    async def add_task_type(self, update: Update, context):
        """添加任务 - 选择类型"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("已取消添加任务")
            return ConversationHandler.END
        
        task_type = query.data.replace("task_type_", "")
        user_id = update.effective_user.id
        
        # 存储临时数据
        self.temp_data[user_id] = {
            'type': task_type,
            'user_id': user_id
        }
        
        if task_type == "group":
            await query.edit_message_text(
                "请输入群组ID或邀请链接:\n"
                "格式: -1001234567890 或 https://t.me/groupname"
            )
        else:
            await query.edit_message_text(
                "请输入Bot用户名:\n"
                "格式: @botname 或 botname"
            )
        
        return ADD_TASK_TARGET
    
    async def add_task_target(self, update: Update, context):
        """添加任务 - 输入目标"""
        user_id = update.effective_user.id
        target = update.message.text.strip()
        
        self.temp_data[user_id]['target'] = target
        
        await update.message.reply_text(
            "请输入签到命令:\n"
            "例如: /checkin, /sign, 签到 等"
        )
        
        return ADD_TASK_COMMAND
    
    async def add_task_command(self, update: Update, context):
        """添加任务 - 输入命令"""
        user_id = update.effective_user.id
        command = update.message.text.strip()
        
        self.temp_data[user_id]['command'] = command
        
        await update.message.reply_text(
            "请设置签到时间 (24小时制，多个时间用逗号分隔):\n"
            "例如: 08:00 或 08:00,20:00\n"
            "时区: 上海时间 (UTC+8)"
        )
        
        return ADD_TASK_TIME
    
    async def add_task_time(self, update: Update, context):
        """添加任务 - 设置时间"""
        user_id = update.effective_user.id
        times = update.message.text.strip()
        
        # 验证时间格式
        time_list = []
        for t in times.split(','):
            t = t.strip()
            try:
                # 验证时间格式
                datetime.strptime(t, "%H:%M")
                time_list.append(t)
            except ValueError:
                await update.message.reply_text(
                    f"❌ 时间格式错误: {t}\n"
                    "请使用 HH:MM 格式，如 08:00"
                )
                return ADD_TASK_TIME
        
        # 创建任务
        task_id = str(uuid.uuid4())[:8]
        task_data = self.temp_data[user_id]
        
        task = {
            'id': task_id,
            'user_id': user_id,
            'type': task_data['type'],
            'target': task_data['target'],
            'command': task_data['command'],
            'schedule_times': time_list,
            'enabled': True,
            'created_at': datetime.now().isoformat(),
            'last_run': None,
            'success_count': 0,
            'fail_count': 0
        }
        
        # 保存任务
        if str(user_id) not in self.config_manager.tasks:
            self.config_manager.tasks[str(user_id)] = []
        
        self.config_manager.tasks[str(user_id)].append(task)
        self.config_manager.save_tasks()
        
        # 注册定时任务
        await self.user_client.register_task(task)
        
        # 清理临时数据
        del self.temp_data[user_id]
        
        await update.message.reply_text(
            f"✅ 任务创建成功！\n\n"
            f"任务ID: {task_id}\n"
            f"类型: {'群组' if task['type'] == 'group' else 'Bot'}签到\n"
            f"目标: {task['target']}\n"
            f"命令: {task['command']}\n"
            f"时间: {', '.join(time_list)} (上海时间)\n"
            f"状态: {'✅ 已启用' if task['enabled'] else '❌ 已禁用'}"
        )
        
        return ConversationHandler.END
    
    async def cmd_list_tasks(self, update: Update, context):
        """查看任务列表"""
        user_id = str(update.effective_user.id)
        tasks = self.config_manager.tasks.get(user_id, [])
        
        if not tasks:
            await update.message.reply_text("您还没有创建任何任务。")
            return
        
        text = "📋 **您的签到任务:**\n\n"
        
        for task in tasks:
            text += f"**任务 {task['id']}**\n"
            text += f"• 类型: {'群组' if task['type'] == 'group' else 'Bot'}签到\n"
            text += f"• 目标: `{task['target']}`\n"
            text += f"• 命令: `{task['command']}`\n"
            text += f"• 时间: {', '.join(task['schedule_times'])}\n"
            text += f"• 状态: {'✅ 启用' if task['enabled'] else '❌ 禁用'}\n"
            text += f"• 统计: 成功 {task['success_count']} / 失败 {task['fail_count']}\n"
            
            if task['last_run']:
                last_run = datetime.fromisoformat(task['last_run'])
                text += f"• 上次运行: {last_run.strftime('%Y-%m-%d %H:%M:%S')}\n"
            
            text += "\n"
        
        # 添加操作按钮
        keyboard = [
            [
                InlineKeyboardButton("✏️ 编辑任务", callback_data="tasks_edit"),
                InlineKeyboardButton("🗑 删除任务", callback_data="tasks_delete")
            ],
            [
                InlineKeyboardButton("🔧 测试任务", callback_data="tasks_test"),
                InlineKeyboardButton("🔄 刷新", callback_data="tasks_refresh")
            ]
        ]
        
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cmd_test_task(self, update: Update, context):
        """测试任务"""
        user_id = str(update.effective_user.id)
        tasks = self.config_manager.tasks.get(user_id, [])
        
        if not tasks:
            await update.message.reply_text("您还没有创建任何任务。")
            return
        
        # 显示任务选择
        keyboard = []
        for task in tasks:
            btn_text = f"{task['id']} - {task['target']}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"test_{task['id']}")])
        
        keyboard.append([InlineKeyboardButton("❌ 取消", callback_data="cancel")])
        
        await update.message.reply_text(
            "请选择要测试的任务:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cmd_add_user(self, update: Update, context):
        """添加授权用户"""
        await update.message.reply_text(
            "请输入要授权的用户ID:\n"
            "格式: 用户ID [admin]\n"
            "例如: 123456789 或 123456789 admin"
        )
        return ADD_USER_ID
    
    async def add_user_process(self, update: Update, context):
        """处理添加用户"""
        text = update.message.text.strip().split()
        
        try:
            user_id = int(text[0])
            is_admin = len(text) > 1 and text[1].lower() == 'admin'
            
            if self.config_manager.add_user(user_id, is_admin=is_admin):
                await update.message.reply_text(
                    f"✅ 成功添加用户!\n"
                    f"用户ID: {user_id}\n"
                    f"权限: {'管理员' if is_admin else '普通用户'}"
                )
            else:
                await update.message.reply_text("该用户已经是授权用户。")
                
        except (ValueError, IndexError):
            await update.message.reply_text("❌ 输入格式错误！")
            return ADD_USER_ID
        
        return ConversationHandler.END
    
    async def cmd_remove_user(self, update: Update, context):
        """移除用户"""
        if len(context.args) == 0:
            await update.message.reply_text(
                "使用方法: /remove_user <user_id>\n"
                "例如: /remove_user 123456789"
            )
            return
        
        try:
            user_id = int(context.args[0])
            
            if user_id == update.effective_user.id:
                await update.message.reply_text("❌ 不能移除自己！")
                return
                
            if self.config_manager.remove_user(user_id):
                await update.message.reply_text(f"✅ 已移除用户 {user_id}")
            else:
                await update.message.reply_text("❌ 用户不存在")
                
        except ValueError:
            await update.message.reply_text("❌ 用户ID必须是数字！")
    
    async def cmd_list_users(self, update: Update, context):
        """查看所有用户"""
        users = self.config_manager.get_all_users()
        
        text = "👥 **授权用户列表:**\n\n"
        
        if users['admin_users']:
            text += "**管理员:**\n"
            for uid in users['admin_users']:
                text += f"• `{uid}`\n"
        
        if users['normal_users']:
            text += "\n**普通用户:**\n"
            for uid in users['normal_users']:
                text += f"• `{uid}`\n"
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def cmd_status(self, update: Update, context):
        """系统状态"""
        # 获取系统状态
        total_tasks = sum(len(tasks) for tasks in self.config_manager.tasks.values())
        enabled_tasks = sum(
            len([t for t in tasks if t['enabled']]) 
            for tasks in self.config_manager.tasks.values()
        )
        total_users = len(self.config_manager.get_all_users()['admin_users']) + \
                     len(self.config_manager.get_all_users()['normal_users'])
        
        client_status = "✅ 已连接" if self.user_client.is_connected() else "❌ 未连接"
        
        status_text = f"""
📊 **系统状态**

**基本信息:**
• 系统版本: v2.0
• 运行时间: {self.get_uptime()}
• 时区: Asia/Shanghai (UTC+8)

**用户统计:**
• 总用户数: {total_users}
• 管理员数: {len(self.config_manager.get_all_users()['admin_users'])}

**任务统计:**
• 总任务数: {total_tasks}
• 启用任务: {enabled_tasks}
• 禁用任务: {total_tasks - enabled_tasks}

**客户端状态:**
• Telegram客户端: {client_status}
• 登录账号: {self.config_manager.config.get('phone_number', '未设置')}
"""
        
        await update.message.reply_text(status_text, parse_mode='Markdown')
    
    async def cmd_settings(self, update: Update, context):
        """系统设置"""
        keyboard = [
            [InlineKeyboardButton("🔐 修改API配置", callback_data="settings_api")],
            [InlineKeyboardButton("📱 修改登录账号", callback_data="settings_account")],
            [InlineKeyboardButton("🔔 通知设置", callback_data="settings_notify")],
            [InlineKeyboardButton("💾 备份数据", callback_data="settings_backup")],
            [InlineKeyboardButton("♻️ 恢复数据", callback_data="settings_restore")]
        ]
        
        await update.message.reply_text(
            "⚙️ **系统设置**",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def button_callback(self, update: Update, context):
        """处理按钮回调"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        # 测试任务
        if data.startswith("test_"):
            task_id = data.replace("test_", "")
            await self.test_single_task(query, task_id)
        
        # 任务操作
        elif data == "tasks_refresh":
            await self.cmd_list_tasks(query, context)
        
        # 设置操作
        elif data.startswith("settings_"):
            await self.handle_settings(query, data)
        
        # 取消操作
        elif data == "cancel":
            await query.edit_message_text("已取消操作")
    
    async def test_single_task(self, query, task_id):
        """测试单个任务"""
        user_id = str(query.from_user.id)
        tasks = self.config_manager.tasks.get(user_id, [])
        
        task = next((t for t in tasks if t['id'] == task_id), None)
        if not task:
            await query.edit_message_text("❌ 任务不存在")
            return
        
        await query.edit_message_text("⏳ 正在测试签到...")
        
        # 执行测试
        success, message = await self.user_client.test_checkin(task)
        
        result_text = f"""
{'✅ 测试成功！' if success else '❌ 测试失败！'}

任务ID: {task_id}
目标: {task['target']}
命令: {task['command']}

结果: {message}
"""
        
        await query.edit_message_text(result_text)
    
    async def handle_settings(self, query, data):
        """处理设置操作"""
        setting_type = data.replace("settings_", "")
        
        if setting_type == "backup":
            # TODO: 实现备份功能
            await query.edit_message_text("📦 备份功能开发中...")
        elif setting_type == "restore":
            # TODO: 实现恢复功能
            await query.edit_message_text("📦 恢复功能开发中...")
        else:
            await query.edit_message_text("🚧 该功能正在开发中...")
    
    async def cancel(self, update: Update, context):
        """取消会话"""
        await update.message.reply_text("已取消当前操作。")
        return ConversationHandler.END
    
    def get_uptime(self):
        """获取运行时间"""
        # TODO: 实现运行时间计算
        return "N/A"
