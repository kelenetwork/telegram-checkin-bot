#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
from typing import Optional, Dict, Any, Union
from telethon import TelegramClient, events, functions, types
from telethon.errors import (
    SessionPasswordNeededError, 
    FloodWaitError, 
    UserPrivacyRestrictedError,
    ChatWriteForbiddenError,
    PeerFloodError
)
from telethon.tl.types import User, Chat, Channel
import pytz
from datetime import datetime
import time
import random

logger = logging.getLogger(__name__)

class UserClient:
    def __init__(self, api_id: str, api_hash: str, session_name: str = "user_session"):
        self.api_id = api_id
        self.api_hash = api_hash
        self.session_name = session_name
        self.client = None
        self.is_connected = False
        self.shanghai_tz = pytz.timezone('Asia/Shanghai')
        self.last_message_time = {}  # 防止发送过于频繁

    async def start(self) -> bool:
        """启动用户客户端"""
        try:
            if not self.api_id or not self.api_hash:
                logger.error("❌ API凭据未配置")
                return False

            self.client = TelegramClient(
                self.session_name,
                int(self.api_id),
                self.api_hash,
                device_model="Telegram Bot",
                system_version="1.0",
                app_version="1.0",
                lang_code="zh",
                system_lang_code="zh"
            )

            await self.client.start()
            
            if not await self.client.is_user_authorized():
                logger.warning("⚠️ 用户未授权，需要登录")
                return False

            self.is_connected = True
            me = await self.client.get_me()
            logger.info(f"✅ 用户客户端已连接: @{me.username or me.first_name}")
            return True

        except Exception as e:
            logger.error(f"❌ 用户客户端启动失败: {e}")
            return False

    async def stop(self):
        """停止客户端"""
        try:
            if self.client:
                await self.client.disconnect()
            self.is_connected = False
            logger.info("✅ 用户客户端已断开")
        except Exception as e:
            logger.error(f"❌ 停止客户端失败: {e}")

    async def login_with_phone(self, phone: str) -> Dict[str, Any]:
        """使用手机号登录"""
        try:
            if not self.client:
                self.client = TelegramClient(
                    self.session_name,
                    int(self.api_id),
                    self.api_hash
                )

            await self.client.connect()
            result = await self.client.send_code_request(phone)
            return {
                "success": True, 
                "message": "验证码已发送",
                "phone_code_hash": result.phone_code_hash
            }

        except Exception as e:
            logger.error(f"❌ 发送验证码失败: {e}")
            return {"success": False, "error": str(e)}

    async def verify_code(self, phone: str, code: str, password: str = None) -> Dict[str, Any]:
        """验证登录码"""
        try:
            if not self.client:
                return {"success": False, "error": "客户端未初始化"}

            try:
                await self.client.sign_in(phone, code)
            except SessionPasswordNeededError:
                if not password:
                    return {"success": False, "need_password": True, "error": "需要两步验证密码"}
                await self.client.sign_in(password=password)

            self.is_connected = True
            me = await self.client.get_me()
            return {
                "success": True,
                "user": {
                    "id": me.id,
                    "username": me.username,
                    "first_name": me.first_name,
                                        "last_name": me.last_name
                }
            }

        except Exception as e:
            logger.error(f"❌ 验证码验证失败: {e}")
            return {"success": False, "error": str(e)}

    async def send_message(self, target: str, message: str, delay: int = None) -> Dict[str, Any]:
        """发送消息"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}

            # 防止发送过于频繁
            now = time.time()
            last_time = self.last_message_time.get(target, 0)
            if now - last_time < 3:  # 至少间隔3秒
                await asyncio.sleep(3 - (now - last_time))

            # 解析目标
            entity = await self.resolve_entity(target)
            if not entity:
                return {"success": False, "error": f"无法找到目标: {target}"}

            # 添加随机延迟
            if delay:
                await asyncio.sleep(random.uniform(1, min(delay, 10)))

            # 发送消息
            sent_msg = await self.client.send_message(entity, message)
            self.last_message_time[target] = time.time()
            
            return {
                "success": True,
                "message_id": sent_msg.id,
                "target": target,
                "timestamp": datetime.now(self.shanghai_tz).strftime("%Y-%m-%d %H:%M:%S")
            }

        except FloodWaitError as e:
            logger.warning(f"⚠️ 触发限流，需要等待 {e.seconds} 秒")
            return {"success": False, "error": f"触发限流，需要等待 {e.seconds} 秒", "retry_after": e.seconds}

        except UserPrivacyRestrictedError:
            return {"success": False, "error": "用户隐私设置限制"}

        except ChatWriteForbiddenError:
            return {"success": False, "error": "无权限在此群组发送消息"}

        except PeerFloodError:
            return {"success": False, "error": "发送消息过于频繁"}

        except Exception as e:
            logger.error(f"❌ 发送消息失败: {e}")
            return {"success": False, "error": str(e)}

    async def resolve_entity(self, target: str):
        """解析目标实体"""
        try:
            if target.startswith('@'):
                # 用户名或频道
                return await self.client.get_entity(target)
            elif target.startswith('https://t.me/'):
                # Telegram链接
                username = target.split('/')[-1]
                if username.startswith('+'):
                    # 私有群组邀请链接
                    return await self.client.get_entity(target)
                else:
                    return await self.client.get_entity('@' + username)
            elif target.isdigit() or (target.startswith('-') and target[1:].isdigit()):
                # ID
                return await self.client.get_entity(int(target))
            else:
                # 尝试作为用户名
                return await self.client.get_entity('@' + target)

        except Exception as e:
            logger.error(f"❌ 解析实体失败 {target}: {e}")
            return None

    async def get_me(self) -> Optional[Dict]:
        """获取当前用户信息"""
        try:
            if not self.is_connected:
                return None

            me = await self.client.get_me()
            return {
                "id": me.id,
                "username": me.username,
                "first_name": me.first_name,
                "last_name": me.last_name,
                "phone": me.phone,
                "is_premium": getattr(me, 'premium', False)
            }
        except Exception as e:
            logger.error(f"❌ 获取用户信息失败: {e}")
            return None

    async def get_dialogs(self, limit: int = 50) -> List[Dict]:
        """获取对话列表"""
        try:
            if not self.is_connected:
                return []

            dialogs = []
            async for dialog in self.client.iter_dialogs(limit=limit):
                entity_info = {
                    "id": dialog.entity.id,
                    "title": dialog.title,
                    "type": "user" if isinstance(dialog.entity, User) else 
                           "group" if isinstance(dialog.entity, Chat) else "channel",
                    "username": getattr(dialog.entity, 'username', None),
                    "unread_count": dialog.unread_count
                }
                dialogs.append(entity_info)

            return dialogs
        except Exception as e:
            logger.error(f"❌ 获取对话列表失败: {e}")
            return []

    async def join_chat(self, invite_link: str) -> Dict[str, Any]:
        """加入群组或频道"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}

            if invite_link.startswith('https://t.me/+'):
                # 私有群组邀请链接
                result = await self.client(functions.messages.ImportChatInviteRequest(
                    hash=invite_link.split('+')[1]
                ))
            else:
                # 公开群组或频道
                username = invite_link.split('/')[-1]
                result = await self.client(functions.channels.JoinChannelRequest(
                    channel=username
                ))

            return {"success": True, "message": "成功加入群组"}

        except Exception as e:
            logger.error(f"❌ 加入群组失败: {e}")
            return {"success": False, "error": str(e)}

    async def leave_chat(self, chat_id: Union[str, int]) -> Dict[str, Any]:
        """离开群组或频道"""
        try:
            if not self.is_connected:
                return {"success": False, "error": "客户端未连接"}

            entity = await self.resolve_entity(str(chat_id))
            if not entity:
                return {"success": False, "error": "无法找到群组"}

            await self.client(functions.channels.LeaveChannelRequest(entity))
            return {"success": True, "message": "成功离开群组"}

        except Exception as e:
            logger.error(f"❌ 离开群组失败: {e}")
            return {"success": False, "error": str(e)}

    async def check_connection(self) -> bool:
        """检查连接状态"""
        try:
            if not self.client or not self.is_connected:
                return False
            
            await self.client.get_me()
            return True
        except Exception as e:
            logger.error(f"❌ 连接检查失败: {e}")
            self.is_connected = False
            return False

