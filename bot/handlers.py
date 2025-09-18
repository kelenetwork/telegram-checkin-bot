"""
Telegram 机器人处理器模块
处理用户发送的普通文本消息，支持对话式交互
"""

import logging
import re
import json
from typing import Dict, Any, Optional, List
from telethon import events
from telethon.types import User

from core.database import DatabaseManager
from core.account_manager import AccountManager
from utils.helpers import is_valid_url, validate_account_data
from utils.permissions import check_user_permission

logger = logging.getLogger(__name__)

class MessageHandler:
    """消息处理器类"""
    
    def __init__(self, bot, config: Dict[str, Any]):
        self.bot = bot
        self.config = config
        self.db = DatabaseManager()
        self.account_manager = AccountManager(config)
        
        # 用户状态存储
        self.user_states = {}
        
        # 注册消息处理器
        self.register_handlers()
    
    def register_handlers(self):
        """注册消息处理器"""
        # 处理所有文本消息（除了命令）
        self.bot.add_event_handler(
            self.handle_text_message,
            events.NewMessage(func=lambda event: (
                event.is_private and 
                not event.message.message.startswith('/') and
                not event.message.via_bot_id
            ))
        )
    
    async def handle_text_message(self, event):
        """处理文本消息"""
        try:
            user_id = event.sender_id
            message_text = event.message.message.strip()
            
            # 权限检查
            if not await check_user_permission(user_id, self.config):
                await event.reply("❌ 您没有使用此机器人的权限。")
                return
            
            # 获取用户状态
            user_state = self.get_user_state(user_id)
            
            if not user_state:
                # 没有状态时的默认处理
                await self.handle_default_message(event, message_text)
            else:
                # 根据状态处理消息
                await self.handle_state_message(event, message_text, user_state)
            
        except Exception as e:
            logger.error(f"处理文本消息时发生错误: {e}")
            await event.reply("处理消息时出现错误，请稍后重试。")
    
    def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户状态"""
        return self.user_states.get(user_id)
    
    def set_user_state(self, user_id: int, state: Dict[str, Any]):
        """设置用户状态"""
        self.user_states[user_id] = state
    
    def clear_user_state(self, user_id: int):
        """清除用户状态"""
        self.user_states.pop(user_id, None)
    
    async def handle_default_message(self, event, message_text: str):
        """处理默认消息（无状态）"""
        try:
            # 检查是否是URL
            if is_valid_url(message_text):
                await self.handle_url_message(event, message_text)
                return
            
            # 检查是否是JSON格式的账号信息
            if message_text.startswith('{') and message_text.endswith('}'):
                await self.handle_json_account(event, message_text)
                return
            
            # 智能回复
            response = await self.generate_smart_reply(message_text)
            await event.reply(response)
            
        except Exception as e:
            logger.error(f"处理默认消息失败: {e}")
            await event.reply("抱歉，我没有理解您的消息。使用 /help 查看帮助。")
    
    async def generate_smart_reply(self, message_text: str) -> str:
        """生成智能回复"""
        message_lower = message_text.lower()
        
        # 关键词匹配回复
        if any(word in message_lower for word in ['你好', 'hello', 'hi', '您好']):
            return "👋 您好！我是自动签到机器人，可以帮助您管理多个网站的签到任务。使用 /start 开始使用。"
        
        elif any(word in message_lower for word in ['帮助', 'help', '怎么用']):
            return "📖 使用 /help 查看详细帮助，或点击 /start 进入主菜单。"
        
        elif any(word in message_lower for word in ['签到', 'checkin', '打卡']):
            return "🔄 使用 /checkin 立即执行签到，或使用 /add 添加新的签到账号。"
        
        elif any(word in message_lower for word in ['账号', 'account', '添加']):
            return "📋 使用 /add 添加新账号，或使用 /accounts 管理现有账号。"
        
        elif any(word in message_lower for word in ['状态', 'status', '统计']):
            return "📊 使用 /status 查看当前状态，或使用 /stats 查看详细统计。"
        
        elif any(word in message_lower for word in ['设置', 'settings', '配置']):
            return "⚙️ 使用 /settings 进入设置菜单，可以配置通知、时间等选项。"
        
        else:
            return (
                "🤔 我没有完全理解您的消息。\n\n"
                "**常用命令：**\n"
                "• /start - 主菜单\n"
                "• /help - 帮助信息\n"
                "• /add - 添加账号\n"
                "• /checkin - 立即签到\n\n"
                "或者您可以直接发送网址来快速添加签到账号。"
            )
    
    async def handle_url_message(self, event, url: str):
        """处理URL消息"""
        try:
            response = f"🔗 **检测到链接**\n\n"
            response += f"链接: {url}\n\n"
            response += "如果这是一个需要签到的网站，您可以：\n"
            response += "1. 点击下方「添加为签到账号」\n"
            response += "2. 按提示输入登录信息\n"
            response += "3. 配置签到参数"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_url_action_keyboard(url)
            
            await event.reply(response, buttons=keyboard, parse_mode='md')
            
        except Exception as e:
            logger.error(f"处理URL消息失败: {e}")
            await event.reply("处理链接失败。")
    
    async def handle_json_account(self, event, json_text: str):
        """处理JSON格式的账号信息"""
        try:
            account_data = json.loads(json_text)
            
            # 验证账号数据
            is_valid, error_msg = validate_account_data(account_data)
            if not is_valid:
                await event.reply(f"❌ 账号信息格式错误：{error_msg}")
                return
            
            response = "📋 **检测到账号信息**\n\n"
            response += f"名称: {account_data.get('name', 'N/A')}\n"
            response += f"类型: {account_data.get('type', 'N/A')}\n"
            response += f"URL: {account_data.get('url', 'N/A')}\n\n"
            response += "确认添加此账号吗？"
            
            from .keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_confirm_account_keyboard(json_text)
            
            await event.reply(response, buttons=keyboard, parse_mode='md')
            
        except json.JSONDecodeError:
            await event.reply("❌ JSON格式错误，请检查后重新发送。")
        except Exception as e:
            logger.error(f"处理JSON账号信息失败: {e}")
            await event.reply("处理账号信息失败。")
    
    async def handle_state_message(self, event, message_text: str, user_state: Dict[str, Any]):
        """根据用户状态处理消息"""
        try:
            state_type = user_state.get('state')
            
            if state_type == 'adding_account':
                await self.handle_adding_account_state(event, message_text, user_state)
            elif state_type == 'editing_account':
                await self.handle_editing_account_state(event, message_text, user_state)
            elif state_type == 'broadcasting':
                await self.handle_broadcasting_state(event, message_text, user_state)
            elif state_type == 'setting_time':
                await self.handle_setting_time_state(event, message_text, user_state)
            else:
                # 未知状态，清除并提示
                self.clear_user_state(event.sender_id)
                await event.reply("状态异常，已重置。请重新操作。")
                
        except Exception as e:
            logger.error(f"处理状态消息失败: {e}")
            await event.reply("处理失败，请稍后重试。")
    
    async def handle_adding_account_state(self, event, message_text: str, user_state: Dict[str, Any]):
        """处理添加账号状态下的消息"""
        try:
            step = user_state.get('step', 'name')
            account_data = user_state.get('account_data', {})
            account_type = user_state.get('account_type', 'web')
            
            if step == 'name':
                # 输入账号名称
                if len(message_text) > 50:
                    await event.reply("❌ 账号名称过长，请不超过50个字符。")
                    return
                
                account_data['name'] = message_text
                account_data['type'] = account_type
                user_state['account_data'] = account_data
                user_state['step'] = 'url'
                
                await event.reply(
                    f"✅ 账号名称: **{message_text}**\n\n"
                    "请输入签到网址:",
                    parse_mode='md'
                )
                
            elif step == 'url':
                # 输入签到URL
                if not is_valid_url(message_text):
                    await event.reply("❌ 请输入有效的网址（以 http:// 或 https:// 开头）")
                    return
                
                account_data['url'] = message_text
                user_state['step'] = 'username'
                
                await event.reply(
                    f"✅ 签到网址: **{message_text}**\n\n"
                    "请输入登录用户名:",
                    parse_mode='md'
                )
                
            elif step == 'username':
                # 输入用户名
                account_data['username'] = message_text
                user_state['step'] = 'password'
                
                await event.reply(
                    f"✅ 用户名: **{message_text}**\n\n"
                    "请输入登录密码:\n"
                    "⚠️ 消息将在处理后自动删除以保护隐私",
                    parse_mode='md'
                )
                
            elif step == 'password':
                # 输入密码
                account_data['password'] = message_text
                user_state['step'] = 'confirm'
                
                # 删除包含密码的消息
                try:
                    await event.delete()
                except:
                    pass
                
                # 显示确认信息
                confirm_text = "📋 **账号信息确认**\n\n"
                confirm_text += f"名称: {account_data['name']}\n"
                confirm_text += f"类型: {account_data['type']}\n"
                confirm_text += f"网址: {account_data['url']}\n"
                confirm_text += f"用户名: {account_data['username']}\n"
                confirm_text += f"密码: {'*' * len(message_text)}\n\n"
                confirm_text += "确认添加此账号吗？"
                
                from .keyboards import KeyboardBuilder
                keyboard = KeyboardBuilder.build_add_account_confirm_keyboard()
                
                await event.reply(confirm_text, buttons=keyboard, parse_mode='md')
                
            # 更新用户状态
            self.set_user_state(event.sender_id, user_state)
            
        except Exception as e:
            logger.error(f"处理添加账号状态失败: {e}")
            await event.reply("添加账号过程中出现错误，请重新开始。")
            self.clear_user_state(event.sender_id)
    
    async def handle_editing_account_state(self, event, message_text: str, user_state: Dict[str, Any]):
        """处理编辑账号状态下的消息"""
        try:
            step = user_state.get('step')
            account_id = user_state.get('account_id')
            
            if not account_id:
                await event.reply("❌ 账号信息丢失，请重新选择要编辑的账号。")
                self.clear_user_state(event.sender_id)
                return
            
            # 根据步骤更新相应字段
            if step == 'name':
                if len(message_text) > 50:
                    await event.reply("❌ 账号名称过长，请不超过50个字符。")
                    return
                
                await self.db.update_account(account_id, {'name': message_text})
                await event.reply(f"✅ 账号名称已更新为: **{message_text}**", parse_mode='md')
                
            elif step == 'url':
                if not is_valid_url(message_text):
                    await event.reply("❌ 请输入有效的网址")
                    return
                
                await self.db.update_account(account_id, {'url': message_text})
                await event.reply(f"✅ 签到网址已更新为: **{message_text}**", parse_mode='md')
                
            elif step == 'username':
                await self.db.update_account(account_id, {'username': message_text})
                await event.reply(f"✅ 用户名已更新为: **{message_text}**", parse_

