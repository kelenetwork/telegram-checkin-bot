"""
验证器模块
提供各种输入验证功能
"""

import re
from typing import Optional, Union, Dict, Any

def validate_phone(phone: str) -> bool:
    """
    验证手机号码格式
    
    Args:
        phone: 手机号码字符串
        
    Returns:
        是否为有效的手机号码
    """
    if not phone:
        return False
    
    # 移除所有非数字字符
    clean_phone = re.sub(r'\D', '', phone)
    
    # 中国手机号码格式验证
    china_pattern = r'^(13[0-9]|14[01456879]|15[0-35-9]|16[2567]|17[0-8]|18[0-9]|19[0-35-9])\d{8}$'
    
    # 国际格式验证 (简化)
    international_pattern = r'^\d{7,15}$'
    
    return (
        re.match(china_pattern, clean_phone) is not None or
        re.match(international_pattern, clean_phone) is not None
    )

def validate_telegram_id(user_id: Union[str, int]) -> bool:
    """
    验证 Telegram 用户ID
    
    Args:
        user_id: 用户ID
        
    Returns:
        是否为有效的 Telegram ID
    """
    try:
        uid = int(user_id)
        # Telegram ID 通常是正整数，范围大致在 1 到 10^10
        return 1 <= uid <= 10**10
    except (ValueError, TypeError):
        return False

def validate_api_credentials(api_id: Union[str, int], api_hash: str) -> Dict[str, Any]:
    """
    验证 Telegram API 凭据
    
    Args:
        api_id: API ID
        api_hash: API Hash
        
    Returns:
        验证结果字典
    """
    result = {
        'valid': True,
        'errors': []
    }
    
    # 验证 API ID
    try:
        aid = int(api_id)
        if aid <= 0:
            result['errors'].append("API ID 必须是正整数")
            result['valid'] = False
    except (ValueError, TypeError):
        result['errors'].append("API ID 格式无效")
        result['valid'] = False
    
    # 验证 API Hash
    if not api_hash:
        result['errors'].append("API Hash 不能为空")
        result['valid'] = False
    elif not isinstance(api_hash, str):
        result['errors'].append("API Hash 必须是字符串")
        result['valid'] = False
    elif len(api_hash) != 32:
        result['errors'].append("API Hash 长度必须是32位")
        result['valid'] = False
    elif not re.match(r'^[a-fA-F0-9]{32}$', api_hash):
        result['errors'].append("API Hash 必须是32位十六进制字符串")
        result['valid'] = False
    
    return result

def validate_bot_token(token: str) -> Dict[str, Any]:
    """
    验证 Telegram Bot Token
    
    Args:
        token: Bot Token
        
    Returns:
        验证结果字典
    """
    result = {
        'valid': True,
        'errors': [],
        'bot_id': None
    }
    
    if not token:
        result['errors'].append("Bot Token 不能为空")
        result['valid'] = False
        return result
    
    # Bot Token 格式: bot_id:auth_token
    # 例: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890
    pattern = r'^(\d+):([A-Za-z0-9_-]{35})$'
    match = re.match(pattern, token)
    
    if not match:
        result['errors'].append("Bot Token 格式无效")
        result['valid'] = False
        return result
    
    bot_id, auth_token = match.groups()
    
    try:
        result['bot_id'] = int(bot_id)
    except ValueError:
        result['errors'].append("Bot ID 格式无效")
        result['valid'] = False
    
    return result

def validate_time_format(time_str: str) -> Dict[str, Any]:
    """
    验证时间格式
    
    Args:
        time_str: 时间字符串
        
    Returns:
        验证结果字典
    """
    result = {
        'valid': True,
        'errors': [],
        'format': None
    }
    
    if not time_str:
        result['errors'].append("时间字符串不能为空")
        result['valid'] = False
        return result
    
    # 支持的时间格式
    formats = [
        (r'^\d{1,2}:\d{2}$', 'HH:MM', '%H:%M'),
        (r'^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{2}$', 'YYYY-MM-DD HH:MM', '%Y-%m-%d %H:%M'),
        (r'^\d{1,2}-\d{1,2} \d{1,2}:\d{2}$', 'MM-DD HH:MM', '%m-%d %H:%M'),
    ]
    
    for pattern, format_name, format_code in formats:
        if re.match(pattern, time_str):
            result['format'] = format_name
            # 尝试解析以验证时间有效性
            try:
                from datetime import datetime
                if format_name == 'HH:MM':
                    hour, minute = map(int, time_str.split(':'))
                    if not (0 <= hour <= 23 and 0 <= minute <= 59):
                        result['errors'].append("时间值超出有效范围")
                        result['valid'] = False
                else:
                    datetime.strptime(time_str, format_code)
            except ValueError as e:
                result['errors'].append(f"时间格式错误: {e}")
                result['valid'] = False
            break
    else:
        result['errors'].append("不支持的时间格式")
        result['valid'] = False
    
    return result

def validate_email(email: str) -> bool:
    """
    验证邮箱地址
    
    Args:
        email: 邮箱地址
        
    Returns:
        是否为有效的邮箱地址
    """
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url: str) -> bool:
    """
    验证URL格式
    
    Args:
        url: URL字符串
        
    Returns:
        是否为有效的URL
    """
    if not url:
        return False
    
    pattern = r'^https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*)?(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?$'
    return re.match(pattern, url) is not None

def validate_username(username: str, min_length: int = 3, max_length: int = 30) -> Dict[str, Any]:
    """
    验证用户名格式
    
    Args:
        username: 用户名
        min_length: 最小长度
        max_length: 最大长度
        
    Returns:
        验证结果字典
    """
    result = {
        'valid': True,
        'errors': []
    }
    
    if not username:
        result['errors'].append("用户名不能为空")
        result['valid'] = False
        return result
    
    # 长度检查
    if len(username) < min_length:
        result['errors'].append(f"用户名长度不能少于 {min_length} 位")
        result['valid'] = False
    
    if len(username) > max_length:
        result['errors'].append(f"用户名长度不能超过 {max_length} 位")
        result['valid'] = False
    
    # 字符检查 (只允许字母、数字、下划线)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        result['errors'].append("用户名只能包含字母、数字和下划线")
        result['valid'] = False
    
    # 不能以数字开头
    if username[0].isdigit():
        result['errors'].append("
        result['errors'].append("用户名不能以数字开头")
        result['valid'] = False
    
    return result

def validate_password(password: str, min_length: int = 6, require_special: bool = False) -> Dict[str, Any]:
    """
    验证密码强度
    
    Args:
        password: 密码
        min_length: 最小长度
        require_special: 是否要求特殊字符
        
    Returns:
        验证结果字典
    """
    result = {
        'valid': True,
        'errors': [],
        'strength': 'weak'  # weak, medium, strong
    }
    
    if not password:
        result['errors'].append("密码不能为空")
        result['valid'] = False
        return result
    
    # 长度检查
    if len(password) < min_length:
        result['errors'].append(f"密码长度不能少于 {min_length} 位")
        result['valid'] = False
    
    # 强度评估
    strength_score = 0
    
    # 包含小写字母
    if re.search(r'[a-z]', password):
        strength_score += 1
    
    # 包含大写字母
    if re.search(r'[A-Z]', password):
        strength_score += 1
    
    # 包含数字
    if re.search(r'\d', password):
        strength_score += 1
    
    # 包含特殊字符
    has_special = re.search(r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]', password)
    if has_special:
        strength_score += 1
    
    # 长度加分
    if len(password) >= 8:
        strength_score += 1
    if len(password) >= 12:
        strength_score += 1
    
    # 要求特殊字符但没有
    if require_special and not has_special:
        result['errors'].append("密码必须包含特殊字符")
        result['valid'] = False
    
    # 评估强度
    if strength_score <= 2:
        result['strength'] = 'weak'
    elif strength_score <= 4:
        result['strength'] = 'medium'
    else:
        result['strength'] = 'strong'
    
    return result

def validate_json_string(json_str: str) -> Dict[str, Any]:
    """
    验证JSON字符串格式
    
    Args:
        json_str: JSON字符串
        
    Returns:
        验证结果字典
    """
    import json
    
    result = {
        'valid': True,
        'errors': [],
        'data': None
    }
    
    if not json_str:
        result['errors'].append("JSON字符串不能为空")
        result['valid'] = False
        return result
    
    try:
        result['data'] = json.loads(json_str)
    except json.JSONDecodeError as e:
        result['errors'].append(f"JSON格式错误: {e}")
        result['valid'] = False
    except Exception as e:
        result['errors'].append(f"解析JSON时发生错误: {e}")
        result['valid'] = False
    
    return result

def validate_file_path(file_path: str, check_exists: bool = False, check_writable: bool = False) -> Dict[str, Any]:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        check_exists: 是否检查文件存在
        check_writable: 是否检查可写权限
        
    Returns:
        验证结果字典
    """
    import os
    
    result = {
        'valid': True,
        'errors': []
    }
    
    if not file_path:
        result['errors'].append("文件路径不能为空")
        result['valid'] = False
        return result
    
    # 检查路径格式
    try:
        os.path.normpath(file_path)
    except Exception:
        result['errors'].append("文件路径格式无效")
        result['valid'] = False
        return result
    
    # 检查文件是否存在
    if check_exists and not os.path.exists(file_path):
        result['errors'].append("文件不存在")
        result['valid'] = False
    
    # 检查目录是否可写
    if check_writable:
        parent_dir = os.path.dirname(file_path) or '.'
        if not os.access(parent_dir, os.W_OK):
            result['errors'].append("没有写入权限")
            result['valid'] = False
    
    return result

def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
        
    Returns:
        清理后的文件名
    """
    if not filename:
        return "untitled"
    
    # 移除或替换非法字符
    illegal_chars = r'[<>:"/\\|?*]'
    clean_name = re.sub(illegal_chars, '_', filename)
    
    # 移除控制字符
    clean_name = re.sub(r'[\x00-\x1f\x7f]', '', clean_name)
    
    # 移除开头结尾的空格和点
    clean_name = clean_name.strip(' .')
    
    # 避免Windows保留名
    reserved_names = [
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    ]
    
    name_without_ext = os.path.splitext(clean_name)[0].upper()
    if name_without_ext in reserved_names:
        clean_name = f"_{clean_name}"
    
    # 截断长度
    if len(clean_name) > max_length:
        name, ext = os.path.splitext(clean_name)
        max_name_length = max_length - len(ext)
        clean_name = name[:max_name_length] + ext
    
    return clean_name or "untitled"

class DataValidator:
    """
    数据验证器类
    """
    
    def __init__(self):
        self.errors = []
    
    def reset(self):
        """重置错误列表"""
        self.errors = []
    
    def add_error(self, field: str, message: str):
        """添加验证错误"""
        self.errors.append({
            'field': field,
            'message': message
        })
    
    def is_valid(self) -> bool:
        """检查是否有错误"""
        return len(self.errors) == 0
    
    def get_errors(self) -> list:
        """获取所有错误"""
        return self.errors.copy()
    
    def validate_required(self, value: Any, field_name: str) -> 'DataValidator':
        """验证必填字段"""
        if value is None or value == "":
            self.add_error(field_name, f"{field_name} 是必填字段")
        return self
    
    def validate_length(self, value: str, field_name: str, min_length: int = 0, max_length: int = None) -> 'DataValidator':
        """验证字符串长度"""
        if value is None:
            return self
        
        if len(value) < min_length:
            self.add_error(field_name, f"{field_name} 长度不能少于 {min_length} 位")
        
        if max_length and len(value) > max_length:
            self.add_error(field_name, f"{field_name} 长度不能超过 {max_length} 位")
        
        return self
    
    def validate_range(self, value: Union[int, float], field_name: str, min_value: Union[int, float] = None, max_value: Union[int, float] = None) -> 'DataValidator':
        """验证数值范围"""
        if value is None:
            return self
        
        if min_value is not None and value < min_value:
            self.add_error(field_name, f"{field_name} 不能小于 {min_value}")
        
        if max_value is not None and value > max_value:
            self.add_error(field_name, f"{field_name} 不能大于 {max_value}")
        
        return self
    
    def validate_pattern(self, value: str, field_name: str, pattern: str, message: str = None) -> 'DataValidator':
        """验证正则表达式模式"""
        if value is None:
            return self
        
        if not re.match(pattern, value):
            error_message = message or f"{field_name} 格式不正确"
            self.add_error(field_name, error_message)
        
        return self
    
    def validate_custom(self, condition: bool, field_name: str, message: str) -> 'DataValidator':
        """自定义验证条件"""
        if not condition:
            self.add_error(field_name, message)
        return self

if __name__ == "__main__":
    # 测试验证器
    print("=== 验证器测试 ===")
    
    # 测试手机号码验证
    test_phones = ["13812345678", "1234567890", "invalid", ""]
    for phone in test_phones:
        print(f"手机号 '{phone}': {validate_phone(phone)}")
    
    # 测试Bot Token验证
    test_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz-1234567890"
    token_result = validate_bot_token(test_token)
    print(f"Bot Token验证: {token_result}")
    
    # 测试时间格式验证
    test_times = ["09:30", "2024-01-01 10:00", "12-25 15:30", "invalid"]
    for time_str in test_times:
        result = validate_time_format(time_str)
        print(f"时间 '{time_str}': 有效={result['valid']}, 格式={result.get('format')}")
    
    # 测试数据验证器
    validator = DataValidator()
    validator.validate_required("", "用户名") \
             .validate_length("abc", "用户名", min_length=5) \
             .validate_range(150, "年龄", min_value=0, max_value=120)
    
    print(f"验证结果: 有效={validator.is_valid()}")
    if not validator.is_valid():
        for error in validator.get_errors():
            print(f"  - {error['field']}: {error['message']}")

