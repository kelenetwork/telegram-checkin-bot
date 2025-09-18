"""
消息发送模块
处理各种类型的消息发送和通知
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class MessageSender:
    """消息发送器"""
    
    def __init__(self, bot_manager, config: Dict[str, Any]):
        self.bot_manager = bot_manager
        self.config = config
        self.message_queue = asyncio.Queue()
        self.rate_limit_delay = 1.0  # 发送间隔（秒）
        self.max_retries = 3
        
    async def send_message(self, user_id: int, text: str, keyboard=None, 
                          parse_mode='markdown', silent: bool = False) -> bool:
        """发送消息"""
        try:
            bot_client = self.bot_manager.get_bot_client()
            
            await bot_client.send_message(
                user_id,
                text,
                buttons=keyboard,
                parse_mode=parse_mode,
                silent=silent
            )
            
            logger.info(f"消息已发送给用户 {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"发送消息失败 (用户 {user_id}): {e}")
            return False
    
    async def send_document(self, user_id: int, file_path: Union[str, Path], 
                           caption: str = None, keyboard=None) -> bool:
        """发送文档"""
        try:
            bot_client = self.bot_manager.get_bot_client()
            
            await bot_client.send_file(
                user_id,
                file_path,
                caption=caption,
                buttons=keyboard
            )
            
            logger.info(f"文档已发送给用户 {user_id}: {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"发送文档失败 (用户 {user_id}): {e}")
            return False
    
    async def send_photo(self, user_id: int, photo_path: Union[str, Path], 
                        caption: str = None, keyboard=None) -> bool:
        """发送图片"""
        try:
            bot_client = self.bot_manager.get_bot_client()
            
            await bot_client.send_file(
                user_id,
                photo_path,
                caption=caption,
                buttons=keyboard
            )
            
            logger.info(f"图片已发送给用户 {user_id}: {photo_path}")
            return True
            
        except Exception as e:
            logger.error(f"发送图片失败 (用户 {user_id}): {e}")
            return False
    
    async def broadcast_message(self, user_ids: List[int], text: str, 
                              keyboard=None, parse_mode='markdown') -> Dict[str, int]:
        """广播消息"""
        results = {"success": 0, "failed": 0}
        
        for user_id in user_ids:
            try:
                success = await self.send_message(
                    user_id, text, keyboard, parse_mode
                )
                
                if success:
                    results["success"] += 1
                else:
                    results["failed"] += 1
                
                # 避免频率限制
                await asyncio.sleep(self.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"广播消息失败 (用户 {user_id}): {e}")
                results["failed"] += 1
        
        logger.info(f"广播完成: 成功 {results['success']}, 失败 {results['failed']}")
        return results
    
    async def send_checkin_notification(self, user_id: int, results: List[Dict[str, Any]]):
        """发送签到结果通知"""
        if not self.config.get('notifications', {}).get('enabled', True):
            return
        
        success_count = len([r for r in results if r.get('success')])
        total_count = len(results)
        
        # 构建消息
        text = f"📊 **签到完成报告**\n\n"
        text += f"✅ 成功: {success_count}/{total_count}\n"
        
        if success_count < total_count:
            failed_results = [r for r in results if not r.get('success')]
            text += f"❌ 失败: {len(failed_results)}\n\n"
            
            text += "**失败详情:**\n"
            for result in failed_results[:5]:  # 只显示前5个失败
                account_name = result.get('account_name', '未知')
                error_msg = result.get('error', '未知错误')
                text += f"• {account_name}: {error_msg}\n"
            
            if len(failed_results) > 5:
                text += f"... 还有 {len(failed_results) - 5} 个失败账号\n"
        
        text += f"\n🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        await self.send_message(user_id, text)
    
    async def send_daily_report(self, user_ids: List[int]):
        """发送日常报告"""
        if not self.config.get('notifications', {}).get('daily_report', False):
            return
        
        try:
            # 这里应该从数据库获取统计数据
            # 为演示目的，使用模拟数据
            
            today = datetime.now().date()
            text = f"📈 **每日签到报告** - {today}\n\n"
            text += "📊 **统计数据:**\n"
            text += "• 总账号数: 待实现\n"
            text += "• 成功签到: 待实现\n"
            text += "• 失败签到: 待实现\n"
            text += "• 签到率: 待实现%\n\n"
            text += "💡 使用 /status 查看详细状态"
            
            await self.broadcast_message(user_ids, text)
            
        except Exception as e:
            logger.error(f"发送日常报告失败: {e}")
    
    async def send_error_notification(self, admin_ids: List[int], error_info: Dict[str, Any]):
        """发送错误通知给管理员"""
        try:
            text = f"🚨 **系统错误通知**\n\n"
            text += f"❌ 错误类型: {error_info.get('type', '未知')}\n"
            text += f"📝 错误信息: {error_info.get('message', '未知错误')}\n"
            text += f"📍 发生位置: {error_info.get('location', '未知')}\n"
            text += f"🕐 时间: {error_info.get('time', datetime.now())}\n"
            
            if error_info.get('user_id'):
                text += f"👤 用户ID: {error_info['user_id']}\n"
            
            await self.broadcast_message(admin_ids, text)
            
        except Exception as e:
            logger.error(f"发送错误通知失败: {e}")
    
    async def send_account_status_update(self, user_id: int, account_name: str, 
                                       old_status: str, new_status: str):
        """发送账号状态更新通知"""
        try:
            status_emoji = {
                'enabled': '✅',
                'disabled': '❌',
                'error': '🔴',
                'success': '🟢'
            }
            
            old_emoji = status_emoji.get(old_status, '❓')
            new_emoji = status_emoji.get(new_status, '❓')
            
            text = f"🔄 **账号状态更新**\n\n"
            text += f"📱 账号: {account_name}\n"
            text += f"📊 状态变更: {old_emoji} {old_status} → {new_emoji} {new_status}\n"
            text += f"🕐 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            await self.send_message(user_id, text)
            
        except Exception as e:
            logger.error(f"发送状态更新通知失败: {e}")
    
    async def send_welcome_message(self, user_id: int, user_name: str = None):
        """发送欢迎消息"""
        try:
            name = user_name or "朋友"
            
            text = f"👋 欢迎您，{name}!\n\n"
            text += "🤖 **Telegram自动签到机器人**\n\n"
            text += "✨ **主要功能:**\n"
            text += "• 🔄 自动签到管理\n"
            text += "• 📊 签到状态查看\n"
            text += "• ⚙️ 账号设置管理\n"
            text += "• 📈 数据统计分析\n\n"
            text += "🚀 **快速开始:**\n"
            text += "1. 使用 /add 添加账号\n"
            text += "2. 使用 /checkin 执行签到\n"
            text += "3. 使用 /status 查看状态\n\n"
            text += "❓ 需要帮助？使用 /help 获取详细说明"
            
            from bot.keyboards import KeyboardBuilder
            keyboard = KeyboardBuilder.build_main_menu()
            
            await self.send_message(user_id, text, keyboard)
            
        except Exception as e:
            logger.error(f"发送欢迎消息失败: {e}")
    
    async def format_checkin_results(self, results: List[Dict[str, Any]]) -> str:
        """格式化签到结果为可读文本"""
        if not results:
            return "❌ 没有签到结果"
        
        success_count = len([r for r in results if r.get('success')])
        total_count = len(results)
        
        text = f"📊 **签到结果摘要**\n\n"
        text += f"✅ 成功: {success_count}/{total_count}\n"
        text += f"❌ 失败: {total_count - success_count}/{total_count}\n"
        text += f"📈 成功率: {(success_count/total_count*100):.1f}%\n\n"
        
        # 成功的账号
        success_results = [r for r in results if r.get('success')]
        if success_results:
            text += "✅ **成功签到:**\n"
            for result in success_results:
                account_name = result.get('account_name', '未知')
                points = result.get('points', 0)
                text += f"• {account_name}"
                if points > 0:
                    text += f" (+{points}分)"
                text += "\n"
            text += "\n"
        
        # 失败的账号
        failed_results = [r for r in results if not r.get('success')]
        if failed_results:
            text += "❌ **签到失败:**\n"
            for result in failed_results:
                account_name = result.get('account_name', '未知')
                error_msg = result.get('error', '未知错误')
                text += f"• {account_name}: {error_msg}\n"
        
        return text

