"""
日志管理模块
提供统一的日志记录功能
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """彩色日志格式器"""
    
    # ANSI 颜色代码
    COLORS = {
        'DEBUG': '\033[36m',      # 青色
        'INFO': '\033[32m',       # 绿色
        'WARNING': '\033[33m',    # 黄色
        'ERROR': '\033[31m',      # 红色
        'CRITICAL': '\033[35m',   # 紫色
    }
    RESET = '\033[0m'
    
    def format(self, record):
        """格式化日志记录"""
        # 保存原始格式
        original_format = self._style._fmt
        
        # 添加颜色
        color = self.COLORS.get(record.levelname, '')
        if color:
            self._style._fmt = f"{color}%(levelname)s{self.RESET} - %(name)s - %(message)s"
        
        # 格式化
        result = super().format(record)
        
        # 恢复原始格式
        self._style._fmt = original_format
        
        return result

class Logger:
    """日志管理器"""
    
    def __init__(self):
        self.loggers = {}
        self.log_dir = "logs"
        self.ensure_log_dir()
    
    def ensure_log_dir(self):
        """确保日志目录存在"""
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
    
    def setup_logger(self, name: str, level: int = logging.INFO, 
                    log_to_file: bool = True, log_to_console: bool = True) -> logging.Logger:
        """
        设置日志记录器
        
        Args:
            name: 日志器名称
            level: 日志级别
            log_to_file: 是否写入文件
            log_to_console: 是否输出到控制台
        """
        if name in self.loggers:
            return self.loggers[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        
        # 清除现有处理器
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        
        # 文件处理器
        if log_to_file:
            # 主日志文件 (轮转)
            log_file = os.path.join(self.log_dir, f"{name}.log")
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
            )
            file_handler.setLevel(level)
            
            # 文件格式 (详细)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
            
            # 错误日志文件 (只记录ERROR及以上)
            if level <= logging.ERROR:
                error_file = os.path.join(self.log_dir, f"{name}_error.log")
                error_handler = logging.handlers.RotatingFileHandler(
                    error_file, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8'
                )
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(file_formatter)
                logger.addHandler(error_handler)
        
        # 控制台处理器
        if log_to_console:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(level)
            
            # 控制台格式 (简洁 + 彩色)
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)
        
        # 缓存logger
        self.loggers[name] = logger
        return logger
    
    def get_logger(self, name: str) -> Optional[logging.Logger]:
        """获取已存在的日志器"""
        return self.loggers.get(name)
    
    def set_level(self, name: str, level: int):
        """设置日志级别"""
        if name in self.loggers:
            self.loggers[name].setLevel(level)
            for handler in self.loggers[name].handlers:
                handler.setLevel(level)

# 全局日志管理器实例
_logger_manager = Logger()

# 便捷函数
def setup_logger(name: str = "main", level: int = logging.INFO, 
                log_to_file: bool = True, log_to_console: bool = True) -> logging.Logger:
    """设置日志记录器"""
    return _logger_manager.setup_logger(name, level, log_to_file, log_to_console)

def get_logger(name: str = "main") -> Optional[logging.Logger]:
    """获取日志记录器"""
    logger = _logger_manager.get_logger(name)
    if logger is None:
        # 如果不存在，创建一个默认的
        logger = setup_logger(name)
    return logger

def set_log_level(name: str, level: int):
    """设置日志级别"""
    _logger_manager.set_level(name, level)

# 预设的日志级别
DEBUG = logging.DEBUG
INFO = logging.INFO  
WARNING = logging.WARNING
ERROR = logging.ERROR
CRITICAL = logging.CRITICAL

if __name__ == "__main__":
    # 测试日志功能
    logger = setup_logger("test", DEBUG)
    
    logger.debug("这是调试信息")
    logger.info("这是一般信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误")
    
    print(f"日志文件位置: {os.path.abspath('logs')}")

