"""
Telegram 机器人命令处理模块
处理用户发送的文本命令
"""

import logging
from typing import Dict, Any, Optional
from telethon import events
from telethon.types import User

from core.database import DatabaseManager
from core.account_manager import AccountManager
from core.task_manager import TaskManager
from utils.helpers import format_time, is_admin
from utils.permissions import check_user_permission

logger = logging.getLogger(__name__)

class CommandHandler:
    """命令处理器类"""
    
    def __init__(self, bot, config: Dict[str, Any]):
        self.bot = bot
        self.config = config
        self.db = DatabaseManager()
        self.account_manager = AccountManager(config)
        self.task_manager = TaskManager(config)
        
        # 注册命令处理器
        self.register_commands()
    
    def register_commands(self):
        """注册所有命令处理器"""
        # 基本命令
        self.bot.add_event_handler(
            self.handle_start,
            events.NewMessage(pattern=r'^/start$')
        )
        
        self.bot.add_event_handler(
            self.handle_help,
            events.NewMessage(pattern=r'^/help$')
        )
        
        self.bot.add_event_handler(
            self.handle_status,
            events.NewMessage(pattern=r'^/status$')
        )
        
        self.bot.add_event_handler(
            self.handle_checkin,
            events.NewMessage(pattern=r'^/checkin$')
        )
        
        # 账号管理命令
        self.bot.add_event_handler(
            self.handle_accounts,
            events.NewMessage(pattern=r'^/accounts$')
        )
        
        self.bot.add_event_handler(
            self.handle_add,
            events.NewMessage(pattern=r'^/add$')
        )
        
        # 设置命令
        self.bot.add_event_handler(
            self.handle_settings,
            events.NewMessage(pattern=r'^/settings$')
        )
        
        self.bot.add_event_handler(
            self.handle_stats,
            events.NewMessage(pattern=r'^/stats$')
        )
        
        # 管理员命令
        self.bot.add_event_handler(
            self.handle_admin,
            events.NewMessage(pattern=r'^/admin$')
        )
        
        self.bot.add_event_handler(
            self.handle_broadcast,
            events.NewMessage(pattern=r'^/broadcast$')
        )
        
        self.bot.add_event_handler(
            self.handle_users,
            events.NewMessage(pattern=r'^/users$')
        )
        
        self.bot.add_event_handler(
            self.handle_logs,
            events.NewMessage(pattern=r'^/logs$')
        )
        
        # 其他命令
        self.bot.add_event_handler(
            self.handle_cancel,
            events.NewMessage(pattern=r'^/cancel$')
        )
    
    async def handle_start(self, event):
        """处理 /start 命令"""
        try:
            user_id = event.sender_id
            user = await event.get_sender()
            
            logger.info(f"用户 {user_id} 发送了 /start 命令")
            
            # 检查用户权限
            if not await check_user_permission(user_id, self.config):
                await event.reply(
                    "❌ **访问受限**\n\n"
                    "抱歉，您没有使用此机器人的权限。\n"
                    "如需帮助，请联系管理员。",
                    parse_mode='md'
                )
                return
            
            # 注册或更新用户信息
            await self.register_user(user)
            
            # 欢迎消息
            welcome_text = f"""
🎉 **欢迎使用自动签到机器人！**

👋 你好 {user.first_name}！

**主要功能：**
• 🔄 多平台自动签到
• ⏰ 智能定时任务
• 📊 详细签到统计
• 🔔 实时状态通知

**快速开始：**
1. 点击下方「添加账号」按钮
2. 根据提示输入签到信息
3. 设置签到时间
4. 享受自动签到服务！

需要帮助？点击「帮助」查看详细说明。
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_main_menu()
            
            await event.reply(
                welcome_text,
                buttons=keyboard,
                parse_mode='md'
            )
            
        except Exception as e:
            logger.error(f"处理 /start 命令时发生错误: {e}")
            await event.reply("启动失败，请稍后重试。")
    
    async def register_user(self, user: User):
        """注册或更新用户信息"""
        try:
            user_data = {
                'user_id': user.id,
                'username': user.username or '',
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'is_bot': user.bot or False,
                'language_code': 'zh-CN',
                'registered_at': None,  # 会在数据库中设置
                'last_active': None,
                'settings': {
                    'notifications_enabled': True,
                    'auto_checkin': True,
                    'timezone': 'Asia/Shanghai',
                    'notifications': {
                        'success': True,
                        'failure': True,
                        'summary': True,
                        'quiet_mode': False
                    }
                }
            }
            
            await self.db.register_user(user_data)
            logger.info(f"用户 {user.id} 注册/更新成功")
            
        except Exception as e:
            logger.error(f"注册用户失败: {e}")
    
    async def handle_help(self, event):
        """处理 /help 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            help_text = """
📖 **使用帮助**

**基本命令：**
/start - 开始使用机器人
/help - 显示此帮助信息
/status - 查看当前状态
/checkin - 手动执行签到

**账号管理：**
/accounts - 查看我的账号
/add - 添加新账号
/settings - 个人设置
/stats - 签到统计

**功能特点：**
• 🔄 支持多种签到方式
• ⏰ 自动定时签到
• 🔔 签到结果通知
• 📊 详细数据统计
• 🛡️ 数据安全保护

**使用流程：**
1. 使用 /add 添加签到账号
2. 在设置中配置签到时间
3. 开启自动签到功能
4. 享受自动签到服务

需要更多帮助？使用按钮菜单获得更好的体验！
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_help_menu()
            
            await event.reply(help_text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /help 命令时发生错误: {e}")
            await event.reply("获取帮助失败，请稍后重试。")
    
    async def handle_status(self, event):
        """处理 /status 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            # 获取用户账号信息
            accounts = await self.db.get_user_accounts(user_id)
            user_settings = await self.db.get_user_settings(user_id)
            
            # 构建状态信息
            status_text = "📊 **当前状态**\n\n"
            
            # 账号状态
            if not accounts:
                status_text += "📋 账号: 暂无\n"
            else:
                enabled_accounts = [acc for acc in accounts if acc.get('enabled', True)]
                status_text += f"📋 账号: {len(enabled_accounts)}/{len(accounts)} 个启用\n"
            
            # 自动签到状态
            auto_checkin = user_settings.get('auto_checkin', True)
            status_text += f"⏰ 自动签到: {'开启' if auto_checkin else '关闭'}\n"
            
            # 通知状态
            notifications = user_settings.get('notifications_enabled', True)
            status_text += f"🔔 通知: {'开启' if notifications else '关闭'}\n"
            
            # 时区设置
            timezone = user_settings.get('timezone', 'Asia/Shanghai')
            status_text += f"🌐 时区: {timezone}\n\n"
            
            # 今日签到统计
            today_stats = await self.db.get_today_stats(user_id)
            if today_stats:
                status_text += f"**今日签到:**\n"
                status_text += f"✅ 成功: {today_stats.get('success', 0)}\n"
                status_text += f"❌ 失败: {today_stats.get('failure', 0)}\n"
                status_text += f"⏳ 待执行: {today_stats.get('pending', 0)}\n"
            
            # 下次签到时间
            next_checkin = await self.task_manager.get_next_checkin_time(user_id)
            if next_checkin:
                status_text += f"\n⏰ 下次签到: {format_time(next_checkin)}"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_status_keyboard()
            
            await event.reply(status_text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /status 命令时发生错误: {e}")
            await event.reply("获取状态失败，请稍后重试。")
    
    async def handle_checkin(self, event):
        """处理 /checkin 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            # 获取用户账号
            accounts = await self.db.get_user_accounts(user_id)
            if not accounts:
                await event.reply(
                    "📋 **暂无签到账号**\n\n"
                    "请先添加签到账号再执行签到操作。\n"
                    "使用 /add 命令添加账号。"
                )
                return
            
            enabled_accounts = [acc for acc in accounts if acc.get('enabled', True)]
            if not enabled_accounts:
                await event.reply(
                    "📋 **暂无可用账号**\n\n"
                    "所有账号都已禁用，请在账号管理中启用账号。"
                )
                return
            
            # 发送执行中消息
            progress_msg = await event.reply("🔄 **正在执行签到...**\n\n请稍候...")
            
            # 执行签到
            results = await self.account_manager.checkin_user_accounts(user_id)
            
            # 统计结果
            success_count = sum(1 for r in results if r['success'])
            total_count = len(results)
            
            # 构建结果消息
            result_text = f"📊 **签到完成**\n\n"
            result_text += f"✅ 成功: {success_count}/{total_count}\n\n"
            
            # 详细结果（最多显示8个）
            for i, result in enumerate(results[:8]):
                status = "✅" if result['success'] else "❌"
                result_text += f"{status} **{result['account_name']}**\n"
                
                if result['success']:
                    if result.get('message'):
                        result_text += f"   {result['message']}\n"
                else:
                    if result.get('error'):
                        error_msg = result['error'][:50] + "..." if len(result['error']) > 50 else result['error']
                        result_text += f"   错误: {error_msg}\n"
                
                result_text += "\n"
            
            if len(results) > 8:
                result_text += f"... 还有 {len(results) - 8} 个结果\n"
            
            # 添加操作按钮
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_checkin_result_keyboard()
            
            await progress_msg.edit(result_text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /checkin 命令时发生错误: {e}")
            await event.reply("执行签到失败，请稍后重试。")
    
    async def handle_accounts(self, event):
        """处理 /accounts 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            accounts = await self.db.get_user_accounts(user_id)
            
            if not accounts:
                text = """
📋 **我的账号**

暂时没有添加任何签到账号。

**开始使用：**
1. 点击下方「添加账号」按钮
2. 选择签到类型（网页/APP）
3. 按提示输入账号信息
4. 设置签到参数

添加成功后即可享受自动签到服务！
                """
            else:
                text = f"📋 **我的账号** (共 {len(accounts)} 个)\
                text = f"📋 **我的账号** (共 {len(accounts)} 个)\n\n"
                
                for i, account in enumerate(accounts[:10], 1):
                    status = "✅" if account.get('enabled', True) else "❌"
                    last_checkin = account.get('last_checkin_time')
                    last_checkin_str = format_time(last_checkin) if last_checkin else "从未签到"
                    
                    text += f"{status} **{account['name']}**\n"
                    text += f"   类型: {account['type']}\n"
                    text += f"   最后签到: {last_checkin_str}\n"
                    text += f"   签到次数: {account.get('checkin_count', 0)}\n\n"
                
                if len(accounts) > 10:
                    text += f"... 还有 {len(accounts) - 10} 个账号\n\n"
                
                text += "点击下方按钮进行详细管理："
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_accounts_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /accounts 命令时发生错误: {e}")
            await event.reply("获取账号列表失败，请稍后重试。")
    
    async def handle_add(self, event):
        """处理 /add 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            text = """
➕ **添加签到账号**

请选择要添加的签到类型：

**🌐 网页签到**
适用于网页版的签到，支持多种网站：
• 论坛签到
• 积分系统
• 会员签到
• 其他网页应用

**📱 APP签到**  
适用于移动应用的签到：
• 移动端API
• 小程序签到
• APP内签到功能

选择类型后，按提示输入相关信息即可。
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_add_account_keyboard()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /add 命令时发生错误: {e}")
            await event.reply("显示添加界面失败，请稍后重试。")
    
    async def handle_settings(self, event):
        """处理 /settings 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            user_settings = await self.db.get_user_settings(user_id)
            
            text = f"""
⚙️ **个人设置**

**基本设置:**
🔔 通知状态: {'开启' if user_settings.get('notifications_enabled', True) else '关闭'}
⏰ 自动签到: {'开启' if user_settings.get('auto_checkin', True) else '关闭'}
🌐 时区: {user_settings.get('timezone', 'Asia/Shanghai')}

**通知设置:**
✅ 成功通知: {'开启' if user_settings.get('notifications', {}).get('success', True) else '关闭'}
❌ 失败通知: {'开启' if user_settings.get('notifications', {}).get('failure', True) else '关闭'}
📊 统计报告: {'开启' if user_settings.get('notifications', {}).get('summary', True) else '关闭'}

**定时设置:**
🕐 签到时间: {user_settings.get('checkin_time', '09:00')}
🔄 重试次数: {user_settings.get('retry_times', 3)}
⏱️ 重试间隔: {user_settings.get('retry_interval', 30)} 秒

点击下方按钮进行详细设置：
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_settings_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /settings 命令时发生错误: {e}")
            await event.reply("获取设置失败，请稍后重试。")
    
    async def handle_stats(self, event):
        """处理 /stats 命令"""
        try:
            user_id = event.sender_id
            
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            # 获取各时间段统计
            today_stats = await self.db.get_user_stats(user_id, 'today')
            week_stats = await self.db.get_user_stats(user_id, 'week') 
            month_stats = await self.db.get_user_stats(user_id, 'month')
            
            text = f"""
📊 **签到统计**

**今日统计:**
📈 签到次数: {today_stats.get('total_checkins', 0)}
✅ 成功: {today_stats.get('success_count', 0)}
❌ 失败: {today_stats.get('failure_count', 0)}
📊 成功率: {today_stats.get('success_rate', 0):.1f}%

**本周统计:**
📈 签到次数: {week_stats.get('total_checkins', 0)}
✅ 成功: {week_stats.get('success_count', 0)}
❌ 失败: {week_stats.get('failure_count', 0)}
📊 成功率: {week_stats.get('success_rate', 0):.1f}%

**本月统计:**
📈 签到次数: {month_stats.get('total_checkins', 0)}
✅ 成功: {month_stats.get('success_count', 0)}
❌ 失败: {month_stats.get('failure_count', 0)}
📊 成功率: {month_stats.get('success_rate', 0):.1f}%

点击下方按钮查看详细统计：
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_stats_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /stats 命令时发生错误: {e}")
            await event.reply("获取统计数据失败，请稍后重试。")
    
    async def handle_admin(self, event):
        """处理 /admin 命令"""
        try:
            user_id = event.sender_id
            
            # 管理员权限检查
            if not is_admin(user_id, self.config):
                await event.reply("❌ 您没有管理员权限。")
                return
            
            # 获取系统统计
            system_stats = await self.get_system_stats()
            
            text = f"""
👑 **管理员面板**

**系统状态:**
🟢 机器人状态: 运行中
⏱️ 运行时间: {system_stats.get('uptime', 'N/A')}
💾 内存使用: {system_stats.get('memory_usage', 'N/A')}MB
💿 磁盘使用: {system_stats.get('disk_usage', 'N/A')}%

**用户统计:**
👥 总用户数: {system_stats.get('total_users', 0)}
🟢 活跃用户: {system_stats.get('active_users', 0)}
📋 总账号数: {system_stats.get('total_accounts', 0)}
🔄 今日签到: {system_stats.get('today_checkins', 0)}

**任务状态:**
⏰ 待执行任务: {system_stats.get('pending_tasks', 0)}
✅ 今日成功: {system_stats.get('today_success', 0)}
❌ 今日失败: {system_stats.get('today_failure', 0)}

点击下方按钮进行管理操作：
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_admin_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /admin 命令时发生错误: {e}")
            await event.reply("获取管理面板失败，请稍后重试。")
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """获取系统统计信息"""
        try:
            import psutil
            import time
            from datetime import datetime, timedelta
            
            # 获取系统信息
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 获取数据库统计
            total_users = await self.db.get_total_users()
            active_users = await self.db.get_active_users_count()
            total_accounts = await self.db.get_total_accounts()
            
            # 获取今日统计
            today_stats = await self.db.get_today_system_stats()
            
            return {
                'uptime': self.format_uptime(),
                'memory_usage': round(memory.used / 1024 / 1024),
                'disk_usage': round(disk.percent),
                'total_users': total_users,
                'active_users': active_users,
                'total_accounts': total_accounts,
                'today_checkins': today_stats.get('total_checkins', 0),
                'today_success': today_stats.get('success_count', 0),
                'today_failure': today_stats.get('failure_count', 0),
                'pending_tasks': await self.task_manager.get_pending_tasks_count()
            }
            
        except Exception as e:
            logger.error(f"获取系统统计失败: {e}")
            return {}
    
    def format_uptime(self) -> str:
        """格式化运行时间"""
        try:
            import psutil
            uptime_seconds = psutil.boot_time()
            uptime = time.time() - uptime_seconds
            
            days = int(uptime // 86400)
            hours = int((uptime % 86400) // 3600)
            minutes = int((uptime % 3600) // 60)
            
            if days > 0:
                return f"{days}天{hours}小时{minutes}分钟"
            elif hours > 0:
                return f"{hours}小时{minutes}分钟"
            else:
                return f"{minutes}分钟"
                
        except Exception:
            return "未知"
    
    async def handle_broadcast(self, event):
        """处理 /broadcast 命令"""
        try:
            user_id = event.sender_id
            
            if not is_admin(user_id, self.config):
                await event.reply("❌ 您没有管理员权限。")
                return
            
            text = """
📢 **广播消息**

此功能可以向所有用户发送消息。

**使用方法:**
1. 点击下方「发送广播」按钮
2. 输入要发送的消息内容
3. 确认后将发送给所有用户

**注意事项:**
• 请谨慎使用此功能
• 避免发送垃圾信息
• 消息将发送给所有注册用户
• 发送过程可能需要一些时间

确定要发送广播消息吗？
            """
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_broadcast_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /broadcast 命令时发生错误: {e}")
            await event.reply("显示广播界面失败，请稍后重试。")
    
    async def handle_users(self, event):
        """处理 /users 命令"""
        try:
            user_id = event.sender_id
            
            if not is_admin(user_id, self.config):
                await event.reply("❌ 您没有管理员权限。")
                return
            
            # 获取用户统计
            users_stats = await self.db.get_users_stats()
            recent_users = await self.db.get_recent_users(10)
            
            text = f"""
👥 **用户管理**

**统计信息:**
📊 总用户数: {users_stats.get('total', 0)}
🟢 活跃用户: {users_stats.get('active', 0)}
🆕 今日新增: {users_stats.get('today_new', 0)}
🔄 今日活跃: {users_stats.get('today_active', 0)}

**最近注册用户:**
            """
            
            for user in recent_users:
                username = user.get('username', 'N/A')
                register_time = format_time(user.get('registered_at'))
                text += f"• {username} ({user['user_id']}) - {register_time}\n"
            
            text += "\n点击下方按钮进行用户管理："
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_user_management_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /users 命令时发生错误: {e}")
            await event.reply("获取用户信息失败，请稍后重试。")
    
    async def handle_logs(self, event):
        """处理 /logs 命令"""
        try:
            user_id = event.sender_id
            
            if not is_admin(user_id, self.config):
                await event.reply("❌ 您没有管理员权限。")
                return
            
            # 获取最近的日志
            recent_logs = await self.get_recent_logs(20)
            
            text = "📋 **系统日志** (最近20条)\n\n"
            
            for log in recent_logs:
                level_emoji = {
                    'INFO': '📝',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'DEBUG': '
                level_emoji = {
                    'INFO': '📝',
                    'WARNING': '⚠️',
                    'ERROR': '❌',
                    'DEBUG': '🔍'
                }.get(log.get('level', 'INFO'), '📝')
                
                timestamp = format_time(log.get('timestamp'))
                message = log.get('message', '')[:80]  # 限制长度
                
                text += f"{level_emoji} {timestamp}\n"
                text += f"   {message}\n\n"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_logs_menu()
            
            await event.reply(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理 /logs 命令时发生错误: {e}")
            await event.reply("获取日志失败，请稍后重试。")
    
    async def get_recent_logs(self, limit: int = 20) -> list:
        """获取最近的日志记录"""
        try:
            # 这里可以从数据库或日志文件中获取日志
            # 暂时返回示例数据
            from datetime import datetime, timedelta
            
            sample_logs = []
            base_time = datetime.now()
            
            for i in range(limit):
                log_time = base_time - timedelta(minutes=i*5)
                sample_logs.append({
                    'timestamp': log_time,
                    'level': ['INFO', 'WARNING', 'ERROR'][i % 3],
                    'message': f'示例日志消息 {i+1}'
                })
            
            return sample_logs
            
        except Exception as e:
            logger.error(f"获取日志失败: {e}")
            return []
    
    async def handle_cancel(self, event):
        """处理 /cancel 命令"""
        try:
            user_id = event.sender_id
            
            # 这里可以清除用户的临时状态
            # 例如取消正在进行的添加账号流程等
            
            await event.reply(
                "✅ **操作已取消**\n\n"
                "已清除当前操作状态。\n"
                "使用 /start 返回主菜单。"
            )
            
        except Exception as e:
            logger.error(f"处理 /cancel 命令时发生错误: {e}")
            await event.reply("取消操作失败。")

