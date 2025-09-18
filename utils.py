# utils.py
import json
import re
import hashlib
import time
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
import logging

logger = logging.getLogger(__name__)

def format_datetime(timestamp: float, timezone: str = "Asia/Shanghai") -> str:
    """格式化时间戳"""
    try:
        tz = pytz.timezone(timezone)
        dt = datetime.fromtimestamp(timestamp, tz)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return "未知时间"

def format_duration(seconds: int) -> str:
    """格式化持续时间"""
    if seconds < 60:
        return f"{seconds}秒"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}分钟"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}天{hours}小时"

def is_valid_telegram_username(username: str) -> bool:
    """验证Telegram用户名格式"""
    pattern = r'^@?[a-zA-Z][a-zA-Z0-9_]{4,31}$'
    return bool(re.match(pattern, username))

def is_valid_telegram_url(url: str) -> bool:
    """验证Telegram链接格式"""
    pattern = r'^https://t\.me/[a-zA-Z][a-zA-Z0-9_]{4,31}$'
    return bool(re.match(pattern, url))

def is_valid_phone_number(phone: str) -> bool:
    """验证手机号格式"""
    pattern = r'^\+?[1-9]\d{7,14}$'
    return bool(re.match(pattern, phone))

def sanitize_filename(filename: str) -> str:
    """清理文件名"""
    # 移除或替换不安全字符
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    
    # 限制长度
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename

def generate_random_string(length: int = 8) -> str:
    """生成随机字符串"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def hash_string(text: str) -> str:
    """生成字符串哈希"""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """截断文本"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix

def parse_time_string(time_str: str) -> Optional[Dict[str, int]]:
    """解析时间字符串 (HH:MM)"""
    try:
        parts = time_str.split(':')
        if len(parts) != 2:
            return None
        
        hour = int(parts[0])
        minute = int(parts[1])
        
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return {"hour": hour, "minute": minute}
        return None
    except ValueError:
        return None

def validate_cron_expression(cron_expr: str) -> bool:
    """验证Cron表达式"""
    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            return False
        
        # 简单验证各部分格式
        for i, part in enumerate(parts):
            if part == '*':
                continue
            
            # 检查数字范围
            if part.isdigit():
                num = int(part)
                if i == 0 and not (0 <= num <= 59):  # 分钟
                    return False
                elif i == 1 and not (0 <= num <= 23):  # 小时
                    return False
                elif i == 2 and not (1 <= num <= 31):  # 日
                    return False
                elif i == 3 and not (1 <= num <= 12):  # 月
                    return False
                elif i == 4 and not (0 <= num <= 6):   # 星期
                    return False
        
        return True
    except Exception:
        return False

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def clean_html_tags(text: str) -> str:
    """清理HTML标签"""
    clean_re = re.compile('<.*?>')
    return re.sub(clean_re, '', text)

def escape_markdown(text: str) -> str:
    """转义Markdown特殊字符"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

def calculate_success_rate(success_count: int, total_count: int) -> float:
    """计算成功率"""
    if total_count == 0:
        return 0.0
    return (success_count / total_count) * 100

def get_next_run_time(schedule: Dict[str, Any], timezone_str: str = "Asia/Shanghai") -> Optional[datetime]:
    """计算下次执行时间"""
    try:
        tz = pytz.timezone(timezone_str)
        now = datetime.now(tz)
        
        if schedule["type"] == "daily":
            # 每日执行
            target_time = now.replace(
                hour=schedule["hour"],
                minute=schedule["minute"],
                second=0,
                microsecond=0
            )
            
            if target_time <= now:
                target_time += timedelta(days=1)
            
            return target_time
            
        elif schedule["type"] == "interval":
            # 间隔执行
            return now + timedelta(minutes=schedule["minutes"])
            
        elif schedule["type"] == "cron":
            # Cron表达式（简单实现）
            # 这里可以使用更完整的Cron解析库
            return None
            
    except Exception as e:
        logger.error(f"❌ 计算下次执行时间失败: {e}")
        return None

def batch_process(items: List[Any], batch_size: int = 100):
    """批处理迭代器"""
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]

def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """重试装饰器"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠️ 第{attempt + 1}次尝试失败，{delay}秒后重试: {e}")
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"❌ 所有重试都失败了: {e}")
            
            raise last_exception
        return wrapper
    return decorator

def validate_json(data: str) -> bool:
    """验证JSON格式"""
    try:
        json.loads(data)
        return True
    except json.JSONDecodeError:
        return False

def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """递归合并字典"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result

def get_system_stats() -> Dict[str, Any]:
    """获取系统统计信息"""
    try:
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_used": memory.used,
            "memory_total": memory.total,
            "disk_percent": (disk.used / disk.total) * 100,
            "disk_used": disk.used,
            "disk_total": disk.total
        }
    except ImportError:
        return {"error": "psutil not installed"}
    except Exception as e:
        return {"error": str(e)}
