#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from typing import Dict, List, Any, Optional
import asyncio
import aiofiles
import time

class ConfigManager:
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config = {
            "bot_token": "",
            "api_id": "",
            "api_hash": "",
            "authorized_users": [],
            "admin_users": [],
            "tasks": {},
            "settings": {
                "timezone": "Asia/Shanghai",
                "log_level": "INFO",
                "max_tasks_per_user": 10,
                "daily_limit": 100
            }
        }
        self.load_config()

    def load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 深度合并配置
                    self._deep_merge(self.config, loaded_config)
            else:
                self.save_config()
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")

    def _deep_merge(self, base: dict, update: dict):
        """深度合并字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def save_config(self):
        """保存配置文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")

    async def save_config_async(self):
        """异步保存配置文件"""
        try:
            async with aiofiles.open(self.config_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.config, ensure_ascii=False, indent=4))
        except Exception as e:
            print(f"❌ 异步保存配置文件失败: {e}")

    # Bot配置
    def get_bot_token(self) -> str:
        return self.config.get("bot_token", "")

    def set_bot_token(self, token: str):
        self.config["bot_token"] = token
        self.save_config()

    def get_api_credentials(self) -> tuple:
        return (
            self.config.get("api_id", ""),
            self.config.get("api_hash", "")
        )

    def set_api_credentials(self, api_id: str, api_hash: str):
        self.config["api_id"] = api_id
        self.config["api_hash"] = api_hash
        self.save_config()

    # 用户权限管理
    def is_authorized_user(self, user_id: int) -> bool:
        return user_id in self.config.get("authorized_users", [])

    def is_admin_user(self, user_id: int) -> bool:
        return user_id in self.config.get("admin_users", [])

    def add_authorized_user(self, user_id: int) -> bool:
        if not self.is_authorized_user(user_id):
            self.config["authorized_users"].append(user_id)
            self.save_config()
            return True
        return False

    def remove_authorized_user(self, user_id: int) -> bool:
        if self.is_authorized_user(user_id):
            self.config["authorized_users"].remove(user_id)
            self.save_config()
            return True
        return False

    def add_admin_user(self, user_id: int) -> bool:
        if not self.is_admin_user(user_id):
            self.config["admin_users"].append(user_id)
            if not self.is_authorized_user(user_id):
                self.add_authorized_user(user_id)
            self.save_config()
            return True
        return False

    def get_authorized_users(self) -> List[int]:
        return self.config.get("authorized_users", [])

    def get_admin_users(self) -> List[int]:
        return self.config.get("admin_users", [])

    # 任务管理
    def get_user_tasks(self, user_id: int) -> List[Dict]:
        user_id_str = str(user_id)
        return self.config["tasks"].get(user_id_str, [])

    def add_task(self, user_id: int, task: Dict) -> bool:
        try:
            user_id_str = str(user_id)
            if user_id_str not in self.config["tasks"]:
                self.config["tasks"][user_id_str] = []
            
            # 检查任务数量限制
            max_tasks = self.config["settings"].get("max_tasks_per_user", 10)
            if len(self.config["tasks"][user_id_str]) >= max_tasks:
                return False
            
            # 生成任务ID
            existing_ids = [t.get("id", 0) for t in self.config["tasks"][user_id_str]]
            task_id = max(existing_ids, default=0) + 1
            
            task["id"] = task_id
            task["user_id"] = user_id
            task["enabled"] = True
            task["created_at"] = time.time()
            task["last_run"] = None
            task["run_count"] = 0
            task["success_count"] = 0
            task["error_count"] = 0
            
            self.config["tasks"][user_id_str].append(task)
            self.save_config()
            return True
        except Exception as e:
            print(f"❌ 添加任务失败: {e}")
            return False

    def update_task(self, user_id: int, task_id: int, updates: Dict) -> bool:
        try:
            user_id_str = str(user_id)
            tasks = self.config["tasks"].get(user_id_str, [])
            
            for task in tasks:
                if task.get("id") == task_id:
                    task.update(updates)
                    self.save_config()
                    return True
            return False
        except Exception as e:
            print(f"❌ 更新任务失败: {e}")
            return False

    def delete_task(self, user_id: int, task_id: int) -> bool:
        try:
            user_id_str = str(user_id)
            tasks = self.config["tasks"].get(user_id_str, [])
            
            for i, task in enumerate(tasks):
                if task.get("id") == task_id:
                    del tasks[i]
                    self.save_config()
                    return True
            return False
        except Exception as e:
            print(f"❌ 删除任务失败: {e}")
            return False

    def get_task(self, user_id: int, task_id: int) -> Optional[Dict]:
        user_id_str = str(user_id)
        tasks = self.config["tasks"].get(user_id_str, [])
        
        for task in tasks:
            if task.get("id") == task_id:
                return task
        return None

    def get_all_enabled_tasks(self) -> List[Dict]:
        """获取所有启用的任务"""
        all_tasks = []
        for user_tasks in self.config["tasks"].values():
            for task in user_tasks:
                if task.get("enabled", True):
                    all_tasks.append(task)
        return all_tasks

    def update_task_stats(self, user_id: int, task_id: int, success: bool = True):
        """更新任务统计"""
        user_id_str = str(user_id)
        tasks = self.config["tasks"].get(user_id_str, [])
        
        for task in tasks:
            if task.get("id") == task_id:
                task["last_run"] = time.time()
                task["run_count"] = task.get("run_count", 0) + 1
                if success:
                    task["success_count"] = task.get("success_count", 0) + 1
                else:
                    task["error_count"] = task.get("error_count", 0) + 1
                self.save_config()
                break

    # 设置管理
    def get_setting(self, key: str, default=None):
        return self.config["settings"].get(key, default)

    def set_setting(self, key: str, value):
        self.config["settings"][key] = value
        self.save_config()

    def get_timezone(self) -> str:
        return self.config["settings"].get("timezone", "Asia/Shanghai")

    # 统计信息
    def get_stats(self) -> Dict:
        total_tasks = sum(len(tasks) for tasks in self.config["tasks"].values())
        enabled_tasks = len(self.get_all_enabled_tasks())
        
        # 计算成功率
        total_runs = 0
        total_success = 0
        for user_tasks in self.config["tasks"].values():
            for task in user_tasks:
                total_runs += task.get("run_count", 0)
                total_success += task.get("success_count", 0)
        
        success_rate = (total_success / total_runs * 100) if total_runs > 0 else 0
        
        return {
            "total_users": len(self.config["authorized_users"]),
            "admin_users": len(self.config["admin_users"]),
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "disabled_tasks": total_tasks - enabled_tasks,
            "total_runs": total_runs,
            "success_rate": round(success_rate, 2)
        }

    # 数据导入导出
    def export_data(self) -> Dict:
        """导出数据"""
        return self.config.copy()

    def import_data(self, data: Dict) -> bool:
        """导入数据"""
        try:
            # 验证数据格式
            required_keys = ["bot_token", "authorized_users", "admin_users", "tasks", "settings"]
            if not all(key in data for key in required_keys):
                return False
            
            self.config = data
            self.save_config()
            return True
        except Exception as e:
            print(f"❌ 导入数据失败: {e}")
            return False
