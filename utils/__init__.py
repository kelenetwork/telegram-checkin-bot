"""
工具模块包
提供日志、权限、配置等通用功能
"""

# 导入常用的工具函数
from .logger import setup_logger, get_logger
from .config_loader import load_config, save_config
from .helpers import format_time, safe_int, truncate_text
from .validators import validate_phone, validate_api_credentials
from .permissions import check_admin, is_authorized_user

__all__ = [
    'setup_logger', 'get_logger',
    'load_config', 'save_config', 
    'format_time', 'safe_int', 'truncate_text',
    'validate_phone', 'validate_api_credentials',
    'check_admin', 'is_authorized_user'
]

__version__ = '1.0.0'

