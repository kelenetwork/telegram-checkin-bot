# -*- coding: utf-8 -*-
"""
用户客户端
使用Telethon实现Telegram用户登录和签到功能
"""

import os
import asyncio
import random
import pytz
from datetime import datetime, time as dt_time
from typing import Tuple, Optional
from telethon import TelegramClient, events
from telethon.tl.functions.messages import SendMessageRequest
from telethon.errors import SessionPasswordNeededError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class UserClient:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.client = None
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone('Asia/Shanghai'))
        self.session_path = os.path.join(self.config_manager.config_dir, "user_session")
        
    def is_connected(self) -> bool:
        """检查客户端是否已连接"""
        return self.client and self.client.is_connected()
    
    async def start(self):
        """启动客户端"""
        api_id = int(self.config_manager.config.get('api_id', 0))
        api_hash = self.config_manager.config.get('api_hash', '')
        phone = self.config_manager.config.get('phone_number', '')
        
        if not all([api_id, api_hash, phone]):
            print("❌ API配置不完整，无法启动用户客户端")
            return
        
        # 创建客户端
        self.client = TelegramClient(
            self.session_path,
            api_id,
            api_hash
        )
        
        # 启动客户端
        await self.client.start(
            phone=phone,
            code_callback=self._code_callback,
            password=self._password_callback
        )
        
        # 获取登录信息
        me = await self.client.get_me()
        print(f"✅ 用户客户端已登录: {me.first_name} (@{me.username})")
        
        # 启动调度器
        self.scheduler.start()
        
        # 加载所有任务
        await self.load_all_tasks()
    
    async def stop(self):
        """停止客户端"""
        if self.scheduler.running:
            self.scheduler.shutdown()
        
        if self.client:
            await self.client.disconnect()
    
    async def _code_callback(self):
        """验证码回调"""
        code = input("请输入Telegram验证码: ")
        return code
    
    async def _password_callback(self):
        """两步验证密码回调"""
        password = input("请输入两步验证密码: ")
        return password
    
    async def load_all_tasks(self):
        """加载所有任务到调度器"""
        for user_id, tasks in self.config_manager.tasks.items():
            for task in tasks:
                if task['enabled']:
                    await self.register_task(task)
    
    async def register_task(self, task: dict):
        """注册定时任务"""
        task_id = f"task_{task['id']}"
        
        # 移除已存在的任务
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)
        
        # 为每个时间点创建定时任务
        for schedule_time in task['schedule_times']:
            hour, minute = map(int, schedule_time.split(':'))
            
            # 添加随机延迟（0-60秒）
            second = random.randint(0, 59)
            
            # 创建触发器
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                second=second,
                timezone=pytz.timezone('Asia/Shanghai')
            )
            
            # 添加任务
            self.scheduler.add_job(
                self.execute_checkin,
                trigger=trigger,
                args=[task],
                id=f"{task_id}_{schedule_time}",
                replace_existing=True
            )
        
        print(f"✅ 已注册任务: {task['id']} - {task['target']}")
    
    async def execute_checkin(self, task: dict):
        """执行签到任务"""
        try:
            # 根据任务类型执行签到
            if task['type'] == 'group':
                success, message = await self._checkin_group(task)
            else:  # bot
                success, message = await self._checkin_bot(task)
            
            # 更新任务统计
            task['last_run'] = datetime.now().isoformat()
            if success:
                task['success_count'] = task.get('success_count', 0) + 1
            else:
                task['fail_count'] = task.get('fail_count', 0) + 1
            
            # 保存任务数据
            self.config_manager.save_tasks()
            
            # 发送通知（如果启用）
            await self._send_notification(task, success, message)
            
            print(f"{'✅' if success else '❌'} 任务 {task['id']}: {message}")
            
        except Exception as e:
            print(f"❌ 执行任务 {task['id']} 出错: {str(e)}")
            task['fail_count'] = task.get('fail_count', 0) + 1
            self.config_manager.save_tasks()
    
    async def _checkin_group(self, task: dict) -> Tuple[bool, str]:
        """群组签到"""
        try:
            # 获取群组实体
            target = task['target']
            if target.startswith('-'):
                # 群组ID
                entity = await self.client.get_entity(int(target))
            else:
                # 群组链接
                entity = await self.client.get_entity(target)
            
            # 发送签到消息
            await self.client.send_message(entity, task['command'])
            
            return True, f"成功发送到 {entity.title}"
            
        except Exception as e:
            return False, f"签到失败: {str(e)}"
    
    async def _checkin_bot(self, task: dict) -> Tuple[bool, str]:
        """Bot签到"""
        try:
            # 获取Bot实体
            bot_username = task['target'].replace('@', '')
            entity = await self.client.get_entity(bot_username)
            
            # 发送签到命令
            await self.client.send_message(entity, task['command'])
            
            # 等待Bot响应（可选）
            await asyncio.sleep(2)
            
            return True, f"成功发送到 @{bot_username}"
            
        except Exception as e:
            return False, f"签到失败: {str(e)}"
    
    async def test_checkin(self, task: dict) -> Tuple[bool, str]:
        """测试签到（立即执行）"""
        if not self.is_connected():
            return False, "客户端未连接"
        
        return await self.execute_checkin(task)
    
    async def _send_notification(self, task: dict, success: bool, message: str):
        """发送签到结果通知"""
        # TODO: 实现通知功能
        pass
