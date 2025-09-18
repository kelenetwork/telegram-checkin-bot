"""
Telegram Bot 模块
包含机器人的核心功能和组件
"""

from .bot_client import TelegramBot, BotManager
from .commands import CommandHandler
from .callbacks import CallbackHandler  
from .handlers import MessageHandler, EventHandler, ErrorHandler
from .keyboards import KeyboardBuilder, DynamicKeyboard, ContextualKeyboard

__all__ = [
    'TelegramBot',
    'BotManager', 
    'CommandHandler',
    'CallbackHandler',
    'MessageHandler',
    'EventHandler', 
    'ErrorHandler',
    'KeyboardBuilder',
    'DynamicKeyboard',
    'ContextualKeyboard'
]

__version__ = '1.0.0'
__author__ = 'Auto Checkin Bot'
__description__ = 'Telegram自动签到机器人'
