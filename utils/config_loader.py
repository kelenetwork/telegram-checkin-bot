"""
配置文件加载和管理模块
支持 JSON 和环境变量配置
"""

import os
import json
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_data = {}
        self._load_config()
    
    def _load_config(self):
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
                logger.info(f"配置文件 {self.config_file} 加载成功")
            else:
                logger.warning(f"配置文件 {self.config_file} 不存在，使用默认配置")
                self.config_data = self._get_default_config()
        except json.JSONDecodeError as e:
            logger.error(f"配置文件格式错误: {e}")
            self.config_data = self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            self.config_data = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "telegram": {
                "bot_token": "",
                "api_id": 0,
                "api_hash": "",
                "admin_id": 0,
                "allowed_users": []
            },
            "schedule": {
                "checkin_time": "09:00",
                "timezone": "Asia/Shanghai",
                "retry_times": 3,
                "retry_interval": 60
            },
            "logging": {
                "level": "INFO",
                "log_to_file": True,
                "log_to_console": True
            },
            "database": {
                "file": "data/users.json"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值，支持点号分隔的嵌套键
        例: config.get("telegram.bot_token")
        """
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """
        设置配置值，支持点号分隔的嵌套键
        """
        keys = key.split('.')
        config = self.config_data
        
        # 确保路径存在
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 设置值
        config[keys[-1]] = value
        logger.debug(f"配置已更新: {key} = {value}")
    
    def save(self) -> bool:
        """保存配置到文件"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.config_file) or '.', exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到 {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            return False
    
    def reload(self):
        """重新加载配置文件"""
        self._load_config()
        logger.info("配置已重新加载")
    
    def get_env_or_config(self, env_key: str, config_key: str, default: Any = None) -> Any:
        """
        优先从环境变量获取值，没有则从配置文件获取
        """
        # 先检查环境变量
        env_value = os.getenv(env_key)
        if env_value is not None:
            # 尝试转换类型
            if isinstance(default, bool):
                return env_value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(default, int):
                try:
                    return int(env_value)
                except ValueError:
                    pass
            elif isinstance(default, float):
                try:
                    return float(env_value)
                except ValueError:
                    pass
            return env_value
        
        # 从配置文件获取
        return self.get(config_key, default)
    
    def update(self, data: Dict[str, Any]):
        """批量更新配置"""
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d
        
        deep_update(self.config_data, data)
        logger.info("配置已批量更新")
    
    def validate_required_fields(self) -> bool:
        """验证必需的配置字段"""
        required_fields = [
            "telegram.bot_token",
            "telegram.api_id", 
            "telegram.api_hash"
        ]
        
        missing_fields = []
        for field in required_fields:
            value = self.get(field)
            if not value:
                missing_fields.append(field)
        
        if missing_fields:
            logger.error(f"缺少必需的配置字段: {', '.join(missing_fields)}")
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """返回配置的字典副本"""
        return self.config_data.copy()

# 全局配置管理器实例
_config_manager = None

def get_config_manager(config_file: str = "config.json") -> ConfigManager:
    """获取配置管理器实例（单例）"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager(config_file)
    return _config_manager

# 便捷函数
def load_config(config_file: str = "config.json") -> ConfigManager:
    """加载配置"""
    return get_config_manager(config_file)

def save_config() -> bool:
    """保存当前配置"""
    if _config_manager:
        return _config_manager.save()
    return False

def get_config(key: str, default: Any = None) -> Any:
    """获取配置值"""
    manager = get_config_manager()
    return manager.get(key, default)

def set_config(key: str, value: Any):
    """设置配置值"""
    manager = get_config_manager()
    manager.set(key, value)

def reload_config():
    """重新加载配置"""
    if _config_manager:
        _config_manager.reload()

def validate_config() -> bool:
    """验证配置"""
    manager = get_config_manager()
    return manager.validate_required_fields()

if __name__ == "__main__":
    # 测试配置功能
    config = load_config("test_config.json")
    
    # 设置测试值
    config.set("test.value", "hello")
    config.set("test.number", 42)
    
    # 获取值
    print("test.value:", config.get("test.value"))
    print("test.number:", config.get("test.number"))
    print("不存在的键:", config.get("not.exist", "默认值"))
    
    # 保存配置
    config.save()
    print("配置已保存到 test_config.json")

