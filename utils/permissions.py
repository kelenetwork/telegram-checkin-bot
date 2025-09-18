"""
权限管理模块
处理用户权限验证和管理
"""

import logging
from typing import Dict, List, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class PermissionManager:
    """权限管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.admin_ids = set(config.get('telegram', {}).get('admin_ids', []))
        self.banned_users = set()
        self.user_permissions = {}
    
    def is_admin(self, user_id: int) -> bool:
        """检查用户是否为管理员"""
        return user_id in self.admin_ids
    
    def is_banned(self, user_id: int) -> bool:
        """检查用户是否被封禁"""
        return user_id in self.banned_users
    
    def ban_user(self, user_id: int) -> bool:
        """封禁用户"""
        try:
            self.banned_users.add(user_id)
            logger.info(f"用户 {user_id} 已被封禁")
            return True
        except Exception as e:
            logger.error(f"封禁用户失败: {e}")
            return False
    
    def unban_user(self, user_id: int) -> bool:
        """解封用户"""
        try:
            self.banned_users.discard(user_id)
            logger.info(f"用户 {user_id} 已被解封")
            return True
        except Exception as e:
            logger.error(f"解封用户失败: {e}")
            return False
    
    def add_admin(self, user_id: int) -> bool:
        """添加管理员"""
        try:
            self.admin_ids.add(user_id)
            logger.info(f"用户 {user_id} 已设为管理员")
            return True
        except Exception as e:
            logger.error(f"添加管理员失败: {e}")
            return False
    
    def remove_admin(self, user_id: int) -> bool:
        """移除管理员"""
        try:
            self.admin_ids.discard(user_id)
            logger.info(f"用户 {user_id} 已取消管理员权限")
            return True
        except Exception as e:
            logger.error(f"移除管理员失败: {e}")
            return False
    
    def get_user_permissions(self, user_id: int) -> Dict[str, bool]:
        """获取用户权限"""
        permissions = {
            'is_admin': self.is_admin(user_id),
            'is_banned': self.is_banned(user_id),
            'can_use_bot': not self.is_banned(user_id),
            'can_manage_users': self.is_admin(user_id),
            'can_broadcast': self.is_admin(user_id),
            'can_view_logs': self.is_admin(user_id),
        }
        
        # 合并自定义权限
        user_perms = self.user_permissions.get(user_id, {})
        permissions.update(user_perms)
        
        return permissions
    
    def set_user_permission(self, user_id: int, permission: str, value: bool):
        """设置用户权限"""
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = {}
        
        self.user_permissions[user_id][permission] = value
        logger.info(f"用户 {user_id} 权限 {permission} 设置为 {value}")


# 全局权限管理器实例
_permission_manager: Optional[PermissionManager] = None

def init_permissions(config: Dict[str, Any]):
    """初始化权限管理器"""
    global _permission_manager
    _permission_manager = PermissionManager(config)
    return _permission_manager

def get_permission_manager() -> Optional[PermissionManager]:
    """获取权限管理器实例"""
    return _permission_manager

def is_admin(user_id: int, config: Dict[str, Any] = None) -> bool:
    """检查用户是否为管理员"""
    if _permission_manager:
        return _permission_manager.is_admin(user_id)
    
    # 备用检查方法
    if config:
        admin_ids = config.get('telegram', {}).get('admin_ids', [])
        return user_id in admin_ids
    
    return False

def is_banned(user_id: int) -> bool:
    """检查用户是否被封禁"""
    if _permission_manager:
        return _permission_manager.is_banned(user_id)
    return False

def require_admin(func):
    """装饰器：要求管理员权限"""
    @wraps(func)
    async def wrapper(self, event, *args, **kwargs):
        user_id = event.sender_id
        
        if not is_admin(user_id, getattr(self, 'config', None)):
            await event.reply("❌ 您没有执行此操作的权限。")
            return
        
        return await func(self, event, *args, **kwargs)
    
    return wrapper

def require_not_banned(func):
    """装饰器：要求用户未被封禁"""
    @wraps(func)
    async def wrapper(self, event, *args, **kwargs):
        user_id = event.sender_id
        
        if is_banned(user_id):
            await event.reply("❌ 您已被封禁，无法使用此功能。")
            return
        
        return await func(self, event, *args, **kwargs)
    
    return wrapper

def check_permissions(user_id: int, required_permissions: List[str]) -> bool:
    """检查用户是否拥有所需权限"""
    if not _permission_manager:
        return False
    
    user_perms = _permission_manager.get_user_permissions(user_id)
    
    for perm in required_permissions:
        if not user_perms.get(perm, False):
            return False
    
    return True

