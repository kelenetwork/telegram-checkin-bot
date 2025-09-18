"""
通用辅助函数模块
提供各种实用的工具函数
"""

import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Union, List, Dict
from urllib.parse import urlparse

def format_time(timestamp: Union[int, float, datetime], format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    格式化时间
    
    Args:
        timestamp: 时间戳、datetime对象
        format_str: 格式字符串
    """
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return str(timestamp)
        
        return dt.strftime(format_str)
    except Exception:
        return str(timestamp)

def format_duration(seconds: Union[int, float]) -> str:
    """
    格式化时间间隔
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时间字符串，如 "1天2小时3分钟"
    """
    if seconds < 0:
        return "0秒"
    
    seconds = int(seconds)
    
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if secs > 0 or not parts:
        parts.append(f"{secs}秒")
    
    return "".join(parts)

def safe_int(value: Any, default: int = 0) -> int:
    """
    安全转换为整数
    
    Args:
        value: 要转换的值
        default: 默认值
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    安全转换为浮点数
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断文本
    
    Args:
        text: 原文本
        max_length: 最大长度
        suffix: 后缀
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def clean_text(text: str) -> str:
    """
    清理文本，移除多余的空白字符
    """
    if not text:
        return ""
    
    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)
    
    # 规范化空白字符
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def extract_urls(text: str) -> List[str]:
    """
    从文本中提取URL
    """
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\$\$,]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    return re.findall(url_pattern, text)

def is_valid_url(url: str) -> bool:
    """
    验证URL是否有效
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def hash_string(text: str, algorithm: str = 'md5') -> str:
    """
    计算字符串哈希值
    
    Args:
        text: 要计算哈希的字符串
        algorithm: 哈希算法 (md5, sha1, sha256)
    """
    text_bytes = text.encode('utf-8')
    
    if algorithm.lower() == 'md5':
        return hashlib.md5(text_bytes).hexdigest()
    elif algorithm.lower() == 'sha1':
        return hashlib.sha1(text_bytes).hexdigest()
    elif algorithm.lower() == 'sha256':
        return hashlib.sha256(text_bytes).hexdigest()
    else:
        return hashlib.md5(text_bytes).hexdigest()

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 延迟倍数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        break
            
            # 所有重试都失败了，抛出最后的异常
            raise last_exception
        
        return wrapper
    return decorator

def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    将列表分块
    
    Args:
        lst: 要分块的列表
        chunk_size: 每块的大小
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]

def merge_dicts(*dicts: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并多个字典
    """
    result = {}
    for d in dicts:
        result.update(d)
    return result

def get_nested_value(data: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    从嵌套字典中获取值
    
    Args:
        data: 数据字典
        key_path: 键路径，用点号分隔，如 "a.b.c"
        default: 默认值
    """
    keys = key_path.split('.')
    value = data
    
    try:
        for key in keys:
            value = value[key]
        return value
    except (KeyError, TypeError):
        return default

def set_nested_value(data: Dict[str, Any], key_path: str, value: Any):
    """
    设置嵌套字典的值
    """
    keys = key_path.split('.')
    current = data
    
    # 确保路径存在
    for key in keys[:-1]:
        
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # 设置最终值
    current[keys[-1]] = value

def format_file_size(size_bytes: int) -> str:
    """
    格式化文件大小
    
    Args:
        size_bytes: 字节数
        
    Returns:
        格式化的大小字符串，如 "1.5 MB"
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    size_bytes = float(size_bytes)
    i = 0
    
    while size_bytes >= 1024.0 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def parse_time_string(time_str: str) -> Optional[datetime]:
    """
    解析时间字符串
    
    支持格式:
    - "HH:MM" (今天)
    - "YYYY-MM-DD HH:MM"
    - "MM-DD HH:MM" (今年)
    """
    try:
        now = datetime.now()
        
        # HH:MM 格式
        if re.match(r'^\d{1,2}:\d{2}$', time_str):
            hour, minute = map(int, time_str.split(':'))
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # YYYY-MM-DD HH:MM 格式
        if re.match(r'^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}$', time_str):
            return datetime.strptime(time_str, '%Y-%m-%d %H:%M')
        
        # MM-DD HH:MM 格式
        if re.match(r'^\d{1,2}-\d{1,2} \d{1,2}:\d{2}$', time_str):
            month_day_time = f"{now.year}-{time_str}"
            return datetime.strptime(month_day_time, '%Y-%m-%d %H:%M')
        
        return None
    except Exception:
        return None

def escape_markdown(text: str) -> str:
    """
    转义 Markdown 特殊字符
    """
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def generate_random_string(length: int = 8, charset: str = None) -> str:
    """
    生成随机字符串
    
    Args:
        length: 字符串长度
        charset: 字符集，默认为字母数字
    """
    import random
    import string
    
    if charset is None:
        charset = string.ascii_letters + string.digits
    
    return ''.join(random.choice(charset) for _ in range(length))

def is_development_mode() -> bool:
    """
    检查是否为开发模式
    """
    import os
    return os.getenv('ENVIRONMENT', '').lower() in ('dev', 'development', 'debug')

def get_memory_usage() -> Dict[str, float]:
    """
    获取内存使用情况
    """
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss / 1024 / 1024,  # MB
            'vms': memory_info.vms / 1024 / 1024,  # MB
            'percent': process.memory_percent()
        }
    except ImportError:
        return {'error': 'psutil not installed'}
    except Exception as e:
        return {'error': str(e)}

class Timer:
    """
    简单的计时器类
    """
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
    def start(self):
        """开始计时"""
        self.start_time = time.time()
        self.end_time = None
    
    def stop(self):
        """停止计时"""
        if self.start_time is None:
            raise RuntimeError("Timer not started")
        self.end_time = time.time()
    
    def elapsed(self) -> float:
        """获取经过的时间（秒）"""
        if self.start_time is None:
            return 0.0
        
        end_time = self.end_time or time.time()
        return end_time - self.start_time
    
    def elapsed_str(self) -> str:
        """获取格式化的经过时间"""
        return format_duration(self.elapsed())
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

if __name__ == "__main__":
    # 测试辅助函数
    print("=== 辅助函数测试 ===")
    
    # 时间格式化
    now = datetime.now()
    print(f"当前时间: {format_time(now)}")
    print(f"时间戳: {format_time(time.time())}")
    
    # 时长格式化
    print(f"3661秒 = {format_duration(3661)}")
    
    # 安全转换
    print(f"safe_int('123'): {safe_int('123')}")
    print(f"safe_int('abc'): {safe_int('abc')}")
    
    # 文本截断
    long_text = "这是一个很长的文本字符串，需要被截断"
    print(f"截断文本: {truncate_text(long_text, 10)}")
    
    # 计时器
    with Timer() as timer:
        time.sleep(0.1)
    print(f"计时结果: {timer.elapsed_str()}")
    
    # 文件大小格式化
    print(f"1048576字节 = {format_file_size(1048576)}")

