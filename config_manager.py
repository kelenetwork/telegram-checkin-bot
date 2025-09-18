# -*- coding: utf-8 -*-
"""
配置管理器
处理所有配置相关操作
"""

import os
import json
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet

class ConfigManager:
    def __init__(self):
        self.config_dir = "config"
        self.config_file = os.path.join(self.config_dir, "config.json")
        self.tasks_file = os.path.join(self.config_dir, "tasks.json")
        self.users_file = os.path.join(self.config_dir, "authorized_users.json")
        
        # 创建配置目录
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 加载配置
        self.config = self.load_config()
        self.tasks = self.load_tasks()
        self.authorized_users = self.load_authorized_users()
        
        # 初始化加密
        self._init_encryption()
    
    def _init_encryption(self):
        """初始化加密密钥"""
        key_file = os.path.join(self.config_dir, ".key")
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                self.cipher = Fernet(f.read())
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            self.cipher = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, data: str) -> str:
        """解密数据"""
        return self.cipher.decrypt(data.encode()).decode()
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return os.path.exists(self.config_file) and self.config.get('configured', False)
    
    def load_config(self) -> dict:
        """加载配置"""
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_config(self):
        """保存配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def load_tasks(self) -> dict:
        """加载任务"""
        if os.path.exists(self.tasks_file):
            with open(self.tasks_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_tasks(self):
        """保存任务"""
        with open(self.tasks_file, 'w', encoding='utf-8') as f:
            json.dump(self.tasks, f, ensure_ascii=False, indent=2)
    
    def load_authorized_users(self) -> dict:
        """加载授权用户"""
        if os.path.exists(self.users_file):
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {"admin_users": [], "normal_users": []}
    
    def save_authorized_users(self):
        """保存授权用户"""
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.authorized_users, f, ensure_ascii=False, indent=2)
    
    async def initial_setup(self):
        """初始配置向导"""
        print("\n=== 初始配置向导 ===\n")
        
        # Bot配置
        print("1. Bot配置")
        self.config['bot_token'] = input("请输入Bot Token: ").strip()
        
        # 管理员配置
        print("\n2. 管理员配置")
        admin_id = input("请输入管理员Telegram ID: ").strip()
        self.authorized_users['admin_users'] = [int(admin_id)]
        self.save_authorized_users()
        
        # API配置
        print("\n3. Telegram API配置 (用于用户登录)")
        print("获取方式: https://my.telegram.org/apps")
        self.config['api_id'] = input("请输入API ID: ").strip()
        self.config['api_hash'] = input("请输入API Hash: ").strip()
        
        # 用户账号配置
        print("\n4. 用户账号配置")
        self.config['phone_number'] = input("请输入手机号 (带国际区号，如+86): ").strip()
        
        # 保存配置
        self.config['configured'] = True
        self.config['created_at'] = datetime.now().isoformat()
        self.save_config()
        
        print("\n✓ 配置完成！")
    
    def is_authorized_user(self, user_id: int) -> bool:
        """检查是否为授权用户"""
        return (user_id in self.authorized_users.get('admin_users', []) or 
                user_id in self.authorized_users.get('normal_users', []))
    
    def is_admin_user(self, user_id: int) -> bool:
        """检查是否为管理员"""
        return user_id in self.authorized_users.get('admin_users', [])
    
    def add_user(self, user_id: int, username: str = None, is_admin: bool = False):
        """添加授权用户"""
        user_list = 'admin_users' if is_admin else 'normal_users'
        if user_id not in self.authorized_users[user_list]:
            self.authorized_users[user_list].append(user_id)
            self.save_authorized_users()
            return True
        return False
    
    def remove_user(self, user_id: int):
        """移除授权用户"""
        removed = False
        for user_list in ['admin_users', 'normal_users']:
            if user_id in self.authorized_users[user_list]:
                self.authorized_users[user_list].remove(user_id)
                removed = True
        if removed:
            self.save_authorized_users()
        return removed
    
    def get_all_users(self) -> dict:
        """获取所有授权用户"""
        return self.authorized_users
