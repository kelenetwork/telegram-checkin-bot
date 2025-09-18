"""
Telegram 机器人回调处理模块
处理内联键盘按钮的回调事件
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from telethon import events
from telethon.types import User

from core.database import DatabaseManager
from core.account_manager import AccountManager
from core.task_manager import TaskManager
from utils.helpers import format_time, safe_int

logger = logging.getLogger(__name__)

class CallbackHandler:
    """回调处理器类"""
    
    def __init__(self, bot, config: Dict[str, Any]):
        self.bot = bot
        self.config = config
        self.db = DatabaseManager()
        self.account_manager = AccountManager(config)
        self.task_manager = TaskManager(config)
        
        # 用户状态缓存
        self.user_states: Dict[int, Dict[str, Any]] = {}
        
        # 注册回调处理器
        self.register_callbacks()
    
    def register_callbacks(self):
        """注册所有回调处理器"""
        self.bot.add_event_handler(
            self.handle_callback,
            events.CallbackQuery()
        )
    
    async def handle_callback(self, event):
        """处理回调查询"""
        try:
            user_id = event.sender_id
            data = event.data.decode('utf-8')
            
            logger.info(f"收到回调查询 - 用户: {user_id}, 数据: {data}")
            
            # 解析回调数据
            callback_data = self.parse_callback_data(data)
            action = callback_data.get('action')
            
            if not action:
                await event.answer("无效的操作", alert=True)
                return
            
            # 权限检查
            if not await self.check_permission(user_id, action):
                await event.answer("您没有权限执行此操作", alert=True)
                return
            
            # 路由到对应的处理方法
            handler_method = getattr(self, f'handle_{action}', None)
            if handler_method:
                await handler_method(event, callback_data)
            else:
                await event.answer(f"未知操作: {action}", alert=True)
                
        except Exception as e:
            logger.error(f"处理回调查询时发生错误: {e}")
            await event.answer("处理请求时发生错误", alert=True)
    
    def parse_callback_data(self, data: str) -> Dict[str, str]:
        """解析回调数据"""
        try:
            # 格式: action:param1:param2
            parts = data.split(':')
            result = {'action': parts[0]}
            
            if len(parts) > 1:
                result['param1'] = parts[1]
            if len(parts) > 2:
                result['param2'] = parts[2]
            if len(parts) > 3:
                result['param3'] = parts[3]
                
            return result
        except Exception:
            return {}
    
    async def check_permission(self, user_id: int, action: str) -> bool:
        """检查用户权限"""
        try:
            # 管理员权限
            admin_actions = ['admin_panel', 'user_manage', 'broadcast', 'system_status']
            if action in admin_actions:
                return user_id == self.config.get('telegram', {}).get('admin_id')
            
            # 普通用户权限
            user_data = await self.db.get_user(user_id)
            return user_data is not None
            
        except Exception as e:
            logger.error(f"权限检查失败: {e}")
            return False
    
    async def handle_main_menu(self, event, callback_data):
        """处理主菜单回调"""
        from .keyboards import KeyboardBuilder
        
        keyboard = KeyboardBuilder.build_main_menu()
        await event.edit(
            "🏠 **主菜单**\n\n请选择您要执行的操作：",
            buttons=keyboard,
            parse_mode='md'
        )
        await event.answer()
    
    async def handle_add_account(self, event, callback_data):
        """处理添加账号回调"""
        user_id = event.sender_id
        account_type = callback_data.get('param1', 'web')
        
        # 设置用户状态
        self.user_states[user_id] = {
            'state': 'adding_account',
            'type': account_type,
            'step': 'name'
        }
        
        from .keyboards import KeyboardBuilder
        keyboard = KeyboardBuilder.build_cancel_keyboard()
        
        type_name = "网页签到" if account_type == 'web' else "APP签到"
        await event.edit(
            f"📝 **添加{type_name}账号**\n\n"
            "请输入账号名称（用于识别）：",
            buttons=keyboard,
            parse_mode='md'
        )
        await event.answer()
    
    async def handle_account_list(self, event, callback_data):
        """处理账号列表回调"""
        user_id = event.sender_id
        page = safe_int(callback_data.get('param1', '1'), 1)
        
        try:
            accounts = await self.db.get_user_accounts(user_id)
            
            if not accounts:
                from .keyboards import KeyboardBuilder
                keyboard = KeyboardBuilder.build_back_keyboard()
                await event.edit(
                    "📋 **我的账号**\n\n"
                    "您还没有添加任何签到账号。\n"
                    "点击「添加账号」开始使用！",
                    buttons=keyboard,
                    parse_mode='md'
                )
                await event.answer()
                return
            
            # 分页处理
            items_per_page = 5
            total_pages = (len(accounts) + items_per_page - 1) // items_per_page
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            page_accounts = accounts[start_idx:end_idx]
            
            # 构建账号列表
            text = f"📋 **我的账号** (第 {page}/{total_pages} 页)\n\n"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_account_list_keyboard(
                page_accounts, page, total_pages
            )
            
            for i, account in enumerate(page_accounts, 1):
                status = "✅" if account.get('enabled', True) else "❌"
                last_checkin = account.get('last_checkin_time')
                last_checkin_str = format_time(last_checkin) if last_checkin else "从未签到"
                
                text += f"{status} **{account['name']}**\n"
                text += f"   类型: {account['type']}\n"
                text += f"   最后签到: {last_checkin_str}\n\n"
            
            await event.edit(text, buttons=keyboard, parse_mode='md')
            await event.answer()
            
        except Exception as e:
            logger.error(f"获取账号列表失败: {e}")
            await event.answer("获取账号列表失败", alert=True)
    
    async def handle_account_detail(self, event, callback_data):
        """处理账号详情回调"""
        user_id = event.sender_id
        account_id = callback_data.get('param1')
        
        if not account_id:
            await event.answer("账号ID无效", alert=True)
            return
        
        try:
            account = await self.db.get_account(user_id, account_id)
            if not account:
                await event.answer("账号不存在", alert=True)
                return
            
            # 构建账号详情
            status = "启用" if account.get('enabled', True) else "禁用"
            last_checkin = account.get('last_checkin_time')
            last_checkin_str = format_time(last_checkin) if last_checkin else "从未签到"
            
            text = f"🔍 **账号详情**\n\n"
            text += f"**名称:** {account['name']}\n"
            text += f"**类型:** {account['type']}\n"
            text += f"**状态:** {status}\n"
            text += f"**最后签到:** {last_checkin_str}\n"
            text += f"**签到次数:** {account.get('checkin_count', 0)}\n"
            text += f"**成功次数:** {account.get('success_count', 0)}\n"
            
            if account.get('last_error'):
                text += f"**最后错误:** {account['last_error']}\n"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_account_detail_keyboard(account_id)
            
            await event.edit(text, buttons=keyboard, parse_mode='md')
            await event.answer()
            
        except Exception as e:
            logger.error(f"获取账号详情失败: {e}")
            await event.answer("获取账号详情失败", alert=True)
    
    async def handle_toggle_account(self, event, callback_data):
        """处理启用/禁用账号回调"""
        user_id = event.sender_id
        account_id = callback_data.get('param1')
        
        if not account_id:
            await event.answer("账号ID无效", alert=True)
            return
        
        try:
            account = await self.db.get_account(user_id, account_id)
            if not account:
                await event.answer("账号不存在", alert=True)
                return
            
            # 切换状态
            new_status = not account.get('enabled', True)
            await self.db.update_account(user_id, account_id, {'enabled': new_status})
            
            status_text = "启用" if new_status else "禁用"
            await event.answer(f"已{status_text}账号 {account['name']}")
            
            # 刷新账号详情
            await self.handle_account_detail(event, callback_data)
            
        except Exception as e:
            logger.error(f"切换账号状态失败: {e}")
            await event.answer("操作失败", alert=True)
    
    async def handle_delete_account(self, event, callback_data):
        """处理删除账号回调"""
        user_id = event.sender_id
        account_id = callback_data.get('param1')
        confirm = callback_data.get('param2')
        
        if not account_id:
            await event.answer("账号ID无效", alert=True)
            return
        
        try:
            account = await self.db.get_account(user_id, account_id)
            if not account:
                await event.answer("账号不存在", alert=True)
                return
            
            if confirm != 'yes':
                # 显示确认对话框
                from .keyboards import KeyboardBuilder
                keyboard = KeyboardBuilder.build_confirm_delete_keyboard(account_id)
                
                await event.edit(
                    f"⚠️ **确认删除**\n\n"
                    f"确定要删除账号「{account['name']}」吗？\n"
                    f"此操作不可撤销！",
                    buttons=keyboard,
                    parse_mode='md'
                )
                await event.answer()
                return
            
            # 执行删除
            await self.db.delete_account(user_id, account_id)
            await event.answer(f"已删除账号 {account['name']}")
            
            # 返回账号列表
            await self.handle_account_list(event, {'param1': '1'})
            
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
            await event.answer("删除失败", alert=True)
    
    async def handle_manual_checkin(self, event, callback_data):
        """处理手动签到回调"""
        user_id = event.sender_id
        account_id = callback_data.get('param1')
        
        if account_id:
            # 单个账号签到
            await self.manual_checkin_single(event, user_id, account_id)
        else:
            # 全部账号签到
            await self.manual_checkin_all(event, user_id)
    
    async def manual_checkin_single(self, event, user_id: int, account_id: str):
        """手动签到单个账号"""
        try:
            account = await self.db.get_account(user_id, account_id)
            if not account:
                await event.answer("账号不存在", alert=True)
                return
            
            await event.answer("正在执行签到...")
            
            # 执行签到
            result = await self.account_manager.checkin_account(user_id, account_id)
            
            if result['success']:
                message = f"✅ {account['name']} 签到成功"
                if result.get('message'):
                    message += f"\n{result['message']}"
            else:
                message = f"❌ {account['name']} 签到失败"
                if result.get('error'):
                    message += f"\n错误: {result['error']}"
            
            # 更新消息
            await event.edit(message, parse_mode='md')
            
        except Exception as e:
            logger.error(f"手动签到失败: {e}")
            await event.edit("签到执行失败")
    
    async def manual_checkin_all(self, event, user_id: int):
        """手动签到所有账号"""
        try:
            accounts = await self.db.get_user_accounts(user_id)
            if not accounts:
                await event.answer("没有可签到的账号", alert=True)
                return
            
            await event.answer("正在执行批量签到...")
            await event.edit("🔄 **正在执行批量签到...**", parse_mode='md')
            
            # 执行批量签到
            results = await self.account_manager.checkin_user_accounts(user_id)
            
            # 统计结果
            success_count = sum(1 for r in results if r['success'])
            total_count = len(results)
            
            # 构建结果消息
            message = f"📊 **批量签到完成**
            # 构建结果消息
            message = f"📊 **批量签到完成**\n\n"
            message += f"✅ 成功: {success_count}/{total_count}\n\n"
            
            # 详细结果
            for result in results[:10]:  # 最多显示10个结果
                status = "✅" if result['success'] else "❌"
                message += f"{status} {result['account_name']}"
                if not result['success'] and result.get('error'):
                    message += f" - {result['error'][:30]}..."
                message += "\n"
            
            if len(results) > 10:
                message += f"\n... 还有 {len(results) - 10} 个结果"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_back_keyboard()
            
            await event.edit(message, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"批量签到失败: {e}")
            await event.edit("批量签到执行失败")
    
    async def handle_settings(self, event, callback_data):
        """处理设置回调"""
        user_id = event.sender_id
        setting_type = callback_data.get('param1', 'main')
        
        try:
            user_settings = await self.db.get_user_settings(user_id)
            
            if setting_type == 'main':
                await self.show_main_settings(event, user_settings)
            elif setting_type == 'notification':
                await self.show_notification_settings(event, user_settings)
            elif setting_type == 'schedule':
                await self.show_schedule_settings(event, user_settings)
            else:
                await event.answer("未知设置类型", alert=True)
                
        except Exception as e:
            logger.error(f"显示设置失败: {e}")
            await event.answer("获取设置失败", alert=True)
    
    async def show_main_settings(self, event, settings: Dict[str, Any]):
        """显示主设置页面"""
        text = "⚙️ **个人设置**\n\n"
        text += f"🔔 通知设置: {'开启' if settings.get('notifications_enabled', True) else '关闭'}\n"
        text += f"⏰ 自动签到: {'开启' if settings.get('auto_checkin', True) else '关闭'}\n"
        text += f"🌐 时区: {settings.get('timezone', 'Asia/Shanghai')}\n"
        
        from .keyboards import KeyboardBuilder
        keyboard = KeyboardBuilder.build_settings_keyboard()
        
        await event.edit(text, buttons=keyboard, parse_mode='md')
        await event.answer()
    
    async def show_notification_settings(self, event, settings: Dict[str, Any]):
        """显示通知设置页面"""
        notifications = settings.get('notifications', {})
        
        text = "🔔 **通知设置**\n\n"
        text += f"✅ 成功通知: {'开启' if notifications.get('success', True) else '关闭'}\n"
        text += f"❌ 失败通知: {'开启' if notifications.get('failure', True) else '关闭'}\n"
        text += f"📊 统计报告: {'开启' if notifications.get('summary', True) else '关闭'}\n"
        text += f"🌙 免打扰模式: {'开启' if notifications.get('quiet_mode', False) else '关闭'}\n"
        
        if notifications.get('quiet_hours'):
            quiet = notifications['quiet_hours']
            text += f"🕐 免打扰时间: {quiet.get('start', '22:00')} - {quiet.get('end', '08:00')}\n"
        
        from .keyboards import KeyboardBuilder
        keyboard = KeyboardBuilder.build_notification_settings_keyboard()
        
        await event.edit(text, buttons=keyboard, parse_mode='md')
        await event.answer()
    
    async def handle_toggle_setting(self, event, callback_data):
        """处理设置开关回调"""
        user_id = event.sender_id
        setting_key = callback_data.get('param1')
        
        if not setting_key:
            await event.answer("设置项无效", alert=True)
            return
        
        try:
            current_settings = await self.db.get_user_settings(user_id)
            
            # 处理嵌套设置
            if '.' in setting_key:
                keys = setting_key.split('.')
                target = current_settings
                for key in keys[:-1]:
                    target = target.setdefault(key, {})
                
                current_value = target.get(keys[-1], True)
                target[keys[-1]] = not current_value
            else:
                current_value = current_settings.get(setting_key, True)
                current_settings[setting_key] = not current_value
            
            # 保存设置
            await self.db.update_user_settings(user_id, current_settings)
            
            status = "开启" if not current_value else "关闭"
            await event.answer(f"已{status}该设置")
            
            # 刷新设置页面
            if setting_key.startswith('notifications.'):
                await self.show_notification_settings(event, current_settings)
            else:
                await self.show_main_settings(event, current_settings)
            
        except Exception as e:
            logger.error(f"切换设置失败: {e}")
            await event.answer("设置失败", alert=True)
    
    async def handle_stats(self, event, callback_data):
        """处理统计回调"""
        user_id = event.sender_id
        period = callback_data.get('param1', 'week')
        
        try:
            stats = await self.db.get_user_stats(user_id, period)
            
            text = f"📊 **签到统计** ({period})\n\n"
            text += f"📈 总签到次数: {stats.get('total_checkins', 0)}\n"
            text += f"✅ 成功次数: {stats.get('success_count', 0)}\n"
            text += f"❌ 失败次数: {stats.get('failure_count', 0)}\n"
            text += f"📊 成功率: {stats.get('success_rate', 0):.1f}%\n\n"
            
            # 账号统计
            account_stats = stats.get('account_stats', [])
            if account_stats:
                text += "**账号详情:**\n"
                for acc_stat in account_stats[:5]:  # 显示前5个
                    text += f"• {acc_stat['name']}: {acc_stat['success']}/{acc_stat['total']}\n"
                
                if len(account_stats) > 5:
                    text += f"... 还有 {len(account_stats) - 5} 个账号\n"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_stats_keyboard(period)
            
            await event.edit(text, buttons=keyboard, parse_mode='md')
            await event.answer()
            
        except Exception as e:
            logger.error(f"获取统计数据失败: {e}")
            await event.answer("获取统计失败", alert=True)
    
    async def handle_admin_panel(self, event, callback_data):
        """处理管理员面板回调"""
        user_id = event.sender_id
        
        # 管理员权限检查
        if user_id != self.config.get('telegram', {}).get('admin_id'):
            await event.answer("您没有管理员权限", alert=True)
            return
        
        try:
            # 获取系统统计
            total_users = await self.db.get_total_users()
            active_users = await self.db.get_active_users_count()
            total_accounts = await self.db.get_total_accounts()
            
            text = f"👑 **管理员面板**\n\n"
            text += f"👥 总用户数: {total_users}\n"
            text += f"🟢 活跃用户: {active_users}\n"
            text += f"📋 总账号数: {total_accounts}\n"
            text += f"🤖 机器人状态: 运行中\n"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_admin_keyboard()
            
            await event.edit(text, buttons=keyboard, parse_mode='md')
            await event.answer()
            
        except Exception as e:
            logger.error(f"显示管理员面板失败: {e}")
            await event.answer("获取系统信息失败", alert=True)
    
    async def handle_broadcast(self, event, callback_data):
        """处理广播消息回调"""
        user_id = event.sender_id
        
        if user_id != self.config.get('telegram', {}).get('admin_id'):
            await event.answer("您没有权限", alert=True)
            return
        
        # 设置管理员状态
        self.user_states[user_id] = {
            'state': 'broadcasting',
            'step': 'message'
        }
        
        from .keyboards import KeyboardBuilder
        keyboard = KeyboardBuilder.build_cancel_keyboard()
        
        await event.edit(
            "📢 **发送广播消息**\n\n"
            "请输入要广播的消息内容：",
            buttons=keyboard,
            parse_mode='md'
        )
        await event.answer()
    
    async def handle_user_manage(self, event, callback_data):
        """处理用户管理回调"""
        user_id = event.sender_id
        action = callback_data.get('param1', 'list')
        target_user = callback_data.get('param2')
        
        if user_id != self.config.get('telegram', {}).get('admin_id'):
            await event.answer("您没有权限", alert=True)
            return
        
        try:
            if action == 'list':
                await self.show_user_list(event)
            elif action == 'detail' and target_user:
                await self.show_user_detail(event, target_user)
            elif action == 'ban' and target_user:
                await self.ban_user(event, target_user)
            elif action == 'unban' and target_user:
                await self.unban_user(event, target_user)
            else:
                await event.answer("操作无效", alert=True)
                
        except Exception as e:
            logger.error(f"用户管理操作失败: {e}")
            await event.answer("操作失败", alert=True)
    
    async def show_user_list(self, event):
        """显示用户列表"""
        try:
            users = await self.db.get_all_users_summary()
            
            text = f"👥 **用户管理** (共 {len(users)} 人)\n\n"
            
            for user in users[:10]:  # 显示前10个用户
                status = "🟢" if user.get('active', True) else "🔴"
                text += f"{status} {user.get('username', 'N/A')} ({user['user_id']})\n"
                text += f"   账号数: {user.get('account_count', 0)}\n"
                text += f"   最后活动: {format_time(user.get('last_active'))}\n\n"
            
            if len(users) > 10:
                text += f"... 还有 {len(users) - 10} 个用户"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_user_manage_keyboard()
            
            await event.edit(text, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"获取用户列表失败: {e}")
            await event.edit("获取用户列表失败")
    
    async def handle_cancel(self, event, callback_data):
        """处理取消操作回调"""
        user_id = event.sender_id
        
        # 清除用户状态
        if user_id in self.user_states:
            del self.user_states[user_id]
        
        await self.handle_main_menu(event, {})
    
    def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户状态"""
        return self.user_states.get(user_id)
    
    def set_user_state(self, user_id: int, state: Dict[str, Any]):
        """设置用户状态"""
        self.user_states[user_id] = state
    
    def clear_user_state(self, user_id: int):
        """清除用户状态"""
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def handle_help(self, event, callback_data):
        """处理帮助回调"""
        help_type = callback_data.get('param1', 'main')
        
        if help_type == 'main':
            text = """
📖 **使用帮助**

**基本功能:**
• 添加签到账号
• 查看账号状态
• 手动执行签到
• 查看签到统计

**自动签到:**
机器人会在设定时间自动执行签到，无需人工干预。

**通知功能:**
签到成功或失败时会及时通知您。

点击下方按钮查看详细帮助 👇
            """
        elif help_type == 'commands':
            text = """
🔧 **命令列表**

**/start** - 开始使用机器人
**/help** - 显示帮助信息
**/status** - 查看当前状态
**/checkin** - 手动执行签到
**/accounts** - 管理账号
**/settings** - 个人设置
**/stats** - 查看统计

**管理员命令:**
**/admin** - 管理员面板
**/broadcast** - 广播消息
**/users** - 用户管理
            """
        elif help_type == 'faq':
            text = """
❓ **常见问题**

**Q: 为什么签到失败?**
A: 请检查账号信息是否正确，目标网站是否正常访问。

**Q: 如何修改签到时间?**
A: 在设置中可以自定义签到时间。

**Q: 机器人会保存我的密码吗?**
A: 所有数据都经过加密存储，确保安全。

**Q: 可以同时管理多个账号吗?**
A: 是的，支持添加多个不同平台的账号。
            """
        else:
            text = "未知帮助类型"
        
        from .keyboards import Keyboar
        from .keyboards import KeyboardBuilder
        keyboard = KeyboardBuilder.build_help_keyboard(help_type)
        
        await event.edit(text, buttons=keyboard, parse_mode='md')
        await event.answer()

