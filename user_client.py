# user_client.py
import asyncio
import logging
from typing import Dict, Any, Optional
from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError, 
    PhoneCodeInvalidError, 
    PhoneCodeExpiredError,
    FloodWaitError,
    ChatWriteForbiddenError,
    UserBannedInChannelError,
    ChatAdminRequiredError
)
from telethon.tl.types import (
    User, Chat, Channel,
    InputPeerUser, InputPeerChat, InputPeerChannel
)
import random
import time

logger = logging.getLogger(__name__)

class UserClient:
    """用户客户端管理类"""
    
    def __init__(self, api_id: int, api_hash: str, session_name: str = "user_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None
        self.is_connected = False
        self.phone_code_hash = None
        self.last_message_time = {}  # 防刷限制
        
    async def initialize(self) -> bool:
        """初始化客户端"""
        try:
            self.client = TelegramClient(
                session=self.session_name,
                api_id=self.api_id,
                api_hash=self.api_hash,
                device_model="Telegram Auto Sender",
                system_version="1.0",
                app_version="1.0",
                lang_code="zh-cn",
                system_lang_code="zh-cn"
            )
            
            # 连接客户端
            await self.client.connect()
            
            # 检查是否已登录
            if await self.client.is_user_authorized():
                self.is_connected = True
                user = await self.client.get_me()
                logger.info(f"✅ 用户客户端已连接: @{user.username}")
                return True
            else:
                logger.info("ℹ️ 用户客户端已连接，但未登录")
                return True
                
        except Exception as e:
            logger.error(f"❌ 初始化用户客户端失败: {e}")
            return False

    async def login_with_phone(self, phone: str) -> Dict[str, Any]:
        """使用手机号开始登录流程"""
        try:
            if not self.client:
                return {"success": False, "error": "客户端未初始化"}
            
            # 发送验证码
            sent = await self.client.send_code_request(phone)
            self.phone_code_hash = sent.phone_code_hash
            
            return {
                "success": True,
                "phone_code_hash": self.phone_code_hash
            }
            
        except FloodWaitError as e:
            error_msg = f"请等待 {e.seconds} 秒后重试"
            logger.error(f"❌ 发送验证码被限制: {error_msg}")
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 发送验证码失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def verify_code(self, phone: str, code: str, password: str = None) -> Dict[str, Any]:
        """验证登录码或密码"""
        try:
            if not self.client or not self.phone_code_hash:
                return {"success": False, "error": "登录流程未开始"}
            
            # 如果提供了密码，则是二步验证
            if password:
                user = await self.client.sign_in(password=password)
            else:
                # 使用验证码登录
                user = await self.client.sign_in(phone, code)
            
            # 登录成功
            self.is_connected = True
            
            return {
                "success": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "phone": user.phone
                }
            }
            
        except SessionPasswordNeededError:
            # 需要二步验证
            return {"success": False, "need_password": True}
            
        except PhoneCodeInvalidError:
            return {"success": False, "error": "验证码错误"}
            
        except PhoneCodeExpiredError:
            return {"success": False, "error": "验证码已过期"}
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ 验证登录失败: {error_msg}")
            return {"success": False, "error": error_msg}

    async def get_me(self) -> Optional[Dict[str, Any]]:
        """获取当前用户信息"""
        try:
            if not self.is_connected:
                return None
                
            user = await self.client.get_me()
            return {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone
            }
            
        except Exception as e:
            logger.error(f"❌ 获取用户信息失败: {e}")
            return None

    async def check_connection(self) -> bool:
        """检查连接状态"""
        try:
            if not self.client:
                return False
                
            if not self.client.is_connected():
                await self.client.connect()
                
            # 检查授权状态
            if await self.client.is_user_authorized():
                self.is_connected = True
                return True
            else:
                self.is_connected = False
                return False
                
        except Exception as e:
            logger.error(f"❌ 检查连接失败: {e}")
            self.is_connected = False
            return False

    async def resolve_entity(self, target: str):
        """解析目标实体"""
        try:
            if not self.is_connected:
                return None
                
            # 处理不同格式的目标
            if target.startswith('@'):
                # 用户名或频道名
                entity = await self.client.get_entity(target)
            elif target.startswith('https://t.me/'):
                # Telegram链接
                username = target.replace('https://t.me/', '').split('?')[0]
                entity = await self.client.get_entity(username)
            elif target.isdigit() or (target.startswith('-') and target[1:].isdigit()):
                # 数字ID
                entity = await self.client.get_entity(int(target))
            else:
                # 尝试作为用户名处理
                entity = await self.client.get_entity(target)
                
            return entity
            
        except Exception as e:
            logger.error(f"❌ 解析目标失败 {target}: {e}")
            return None

    async def send_message(self, target: str, message: str) -> Dict[str, Any]:
        """发送消息"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
            
            # 防刷限制检查
            current_time = time.time()
            last_time = self.last_message_time.get(target, 0)
            
            if current_time - last_time < 5:  # 5秒间隔
                wait_time = 5 - (current_time - last_time)
                await asyncio.sleep(wait_time)
            
            # 解析目标
            entity = await self.resolve_entity(target)
            if not entity:
                return {"success": False, "error": f"无法找到目标: {target}"}
            
            # 添加随机延迟，模拟人工操作
            delay = random.uniform(1, 3)
            await asyncio.sleep(delay)
            
            # 发送消息
            sent_message = await self.client.send_message(entity, message)
            
            # 更新最后发送时间
            self.last_message_time[target] = time.time()
            
            logger.info(f"✅ 消息已发送到 {target}: {message[:50]}...")
            
            return {
                "success": True,
                "message_id": sent_message.id,
                "date": sent_message.date
            }
            
        except FloodWaitError as e:
            error_msg = f"发送频率过高，请等待 {e.seconds} 秒"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
        except ChatWriteForbiddenError:
            error_msg = "没有权限发送消息到此聊天"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
        except UserBannedInChannelError:
            error_msg = "您已被此频道封禁"
                        logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
        except ChatAdminRequiredError:
            error_msg = "需要管理员权限才能发送消息"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}
            
        except Exception as e:
            error_msg = f"发送消息失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def get_entity_info(self, target: str) -> Optional[Dict[str, Any]]:
        """获取实体信息"""
        try:
            entity = await self.resolve_entity(target)
            if not entity:
                return None
                
            info = {
                "id": entity.id,
                "type": "",
                "title": "",
                "username": None,
                "member_count": 0
            }
            
            if isinstance(entity, User):
                info["type"] = "user"
                info["title"] = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
                info["username"] = entity.username
                
            elif isinstance(entity, Chat):
                info["type"] = "group"
                info["title"] = entity.title
                info["member_count"] = entity.participants_count
                
            elif isinstance(entity, Channel):
                info["type"] = "channel" if entity.broadcast else "supergroup"
                info["title"] = entity.title
                info["username"] = entity.username
                info["member_count"] = entity.participants_count
                
            return info
            
        except Exception as e:
            logger.error(f"❌ 获取实体信息失败: {e}")
            return None

    async def get_dialogs(self, limit: int = 100) -> list:
        """获取对话列表"""
        try:
            if not self.is_connected:
                return []
                
            dialogs = []
            async for dialog in self.client.iter_dialogs(limit=limit):
                entity = dialog.entity
                
                dialog_info = {
                    "id": entity.id,
                    "title": dialog.title,
                    "type": "",
                    "username": None,
                    "unread_count": dialog.unread_count
                }
                
                if isinstance(entity, User):
                    dialog_info["type"] = "user"
                    dialog_info["username"] = entity.username
                elif isinstance(entity, Chat):
                    dialog_info["type"] = "group"
                elif isinstance(entity, Channel):
                    dialog_info["type"] = "channel" if entity.broadcast else "supergroup"
                    dialog_info["username"] = entity.username
                    
                dialogs.append(dialog_info)
                
            return dialogs
            
        except Exception as e:
            logger.error(f"❌ 获取对话列表失败: {e}")
            return []

    async def send_file(self, target: str, file_path: str, caption: str = "") -> Dict[str, Any]:
        """发送文件"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
                
            entity = await self.resolve_entity(target)
            if not entity:
                return {"success": False, "error": f"无法找到目标: {target}"}
                
            # 添加随机延迟
            delay = random.uniform(2, 5)
            await asyncio.sleep(delay)
            
            # 发送文件
            sent_message = await self.client.send_file(
                entity, 
                file_path, 
                caption=caption
            )
            
            logger.info(f"✅ 文件已发送到 {target}: {file_path}")
            
            return {
                "success": True,
                "message_id": sent_message.id,
                "date": sent_message.date
            }
            
        except Exception as e:
            error_msg = f"发送文件失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def forward_message(self, from_target: str, to_target: str, message_id: int) -> Dict[str, Any]:
        """转发消息"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
                
            from_entity = await self.resolve_entity(from_target)
            to_entity = await self.resolve_entity(to_target)
            
            if not from_entity or not to_entity:
                return {"success": False, "error": "无法找到目标"}
                
            # 转发消息
            await self.client.forward_messages(to_entity, message_id, from_entity)
            
            logger.info(f"✅ 消息已从 {from_target} 转发到 {to_target}")
            
            return {"success": True}
            
        except Exception as e:
            error_msg = f"转发消息失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def join_channel(self, target: str) -> Dict[str, Any]:
        """加入频道或群组"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
                
            # 添加随机延迟
            delay = random.uniform(3, 8)
            await asyncio.sleep(delay)
            
            # 解析并加入
            entity = await self.client.get_entity(target)
            await self.client(functions.channels.JoinChannelRequest(entity))
            
            logger.info(f"✅ 已加入 {target}")
            
            return {"success": True}
            
        except Exception as e:
            error_msg = f"加入失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def leave_channel(self, target: str) -> Dict[str, Any]:
        """离开频道或群组"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
                
            entity = await self.resolve_entity(target)
            if not entity:
                return {"success": False, "error": f"无法找到目标: {target}"}
                
            await self.client(functions.channels.LeaveChannelRequest(entity))
            
            logger.info(f"✅ 已离开 {target}")
            
            return {"success": True}
            
        except Exception as e:
            error_msg = f"离开失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def get_message_history(self, target: str, limit: int = 100) -> list:
        """获取消息历史"""
        try:
            if not self.is_connected:
                return []
                
            entity = await self.resolve_entity(target)
            if not entity:
                return []
                
            messages = []
            async for message in self.client.iter_messages(entity, limit=limit):
                if message.text:
                    messages.append({
                        "id": message.id,
                        "text": message.text,
                        "date": message.date,
                        "sender_id": message.sender_id
                    })
                    
            return messages
            
        except Exception as e:
            logger.error(f"❌ 获取消息历史失败: {e}")
            return []

    async def delete_message(self, target: str, message_id: int) -> Dict[str, Any]:
        """删除消息"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
                
            entity = await self.resolve_entity(target)
            if not entity:
                return {"success": False, "error": f"无法找到目标: {target}"}
                
            await self.client.delete_messages(entity, [message_id])
            
            logger.info(f"✅ 消息 {message_id} 已删除")
            
            return {"success": True}
            
        except Exception as e:
            error_msg = f"删除消息失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def edit_message(self, target: str, message_id: int, new_text: str) -> Dict[str, Any]:
        """编辑消息"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}
                
            entity = await self.resolve_entity(target)
            if not entity:
                return {"success": False, "error": f"无法找到目标: {target}"}
                
            await self.client.edit_message(entity, message_id, new_text)
            
            logger.info(f"✅ 消息 {message_id} 已编辑")
            
            return {"success": True}
            
        except Exception as e:
            error_msg = f"编辑消息失败: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return {"success": False, "error": error_msg}

    async def get_participants(self, target: str, limit: int = 100) -> list:
        """获取群组成员列表"""
        try:
            if not self.is_connected:
                return []
                
            entity = await self.resolve_entity(target)
            if not entity:
                return []
                
            participants = []
            async for user in self.client.iter_participants(entity, limit=limit):
                participants.append({
                    "id": user.id,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_bot": user.bot
                })
                
            return participants
            
        except Exception as e:
            logger.error(f"❌ 获取成员列表失败: {e}")
            return []

    async def disconnect(self):
        """断开连接"""
        try:
            if self.client and self.client.is_connected():
                await self.client.disconnect()
                
            self.is_connected = False
            logger.info("✅ 用户客户端已断开连接")
            
        except Exception as e:
            logger.error(f"❌ 断开连接失败: {e}")

    def get_session_info(self) -> Dict[str, Any]:
        """获取会话信息"""
        try:
            if not self.client:
                return {"connected": False}
                
            return {
                "connected": self.is_connected,
                "authorized": self.client.is_user_authorized() if self.client.is_connected() else False,
                "session_name": self.session_name
            }
            
        except Exception as e:
            logger.error(f"❌ 获取会话信息失败: {e}")
            return {"connected": False}

    async def test_connection(self) -> Dict[str, Any]:
        """测试连接"""
        try:
            if not await self.check_connection():
                return {"success": False, "error": "连接失败"}
                
            # 获取自己的信息来测试连接
            me = await self.get_me()
            if me:
                return {
                    "success": True,
                    "user": me,
                    "message": "连接正常"
                }
            else:
                return {"success": False, "error": "无法获取用户信息"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    def __del__(self):
        """析构函数"""
        try:
            if hasattr(self, 'client') and self.client:
                asyncio.create_task(self.disconnect())
        except Exception:
            pass

