"""
Telegram 机器人键盘构建模块
构建各种内联键盘和回复键盘
"""

import logging
from typing import List, Dict, Any, Optional
from telethon import Button
from telethon.types import KeyboardButtonCallback, KeyboardButtonUrl

logger = logging.getLogger(__name__)

class KeyboardBuilder:
    """键盘构建器类"""
    
    @staticmethod
    def build_main_menu() -> List[List[Button]]:
        """构建主菜单键盘"""
        return [
            [
                Button.inline("🔄 立即签到", b"action:checkin_now"),
                Button.inline("📊 签到状态", b"action:status")
            ],
            [
                Button.inline("📋 我的账号", b"action:accounts"),
                Button.inline("➕ 添加账号", b"action:add_account")
            ],
            [
                Button.inline("📈 统计数据", b"action:stats"),
                Button.inline("⚙️ 设置", b"action:settings")
            ],
            [
                Button.inline("❓ 帮助", b"action:help"),
                Button.inline("ℹ️ 关于", b"action:about")
            ]
        ]
    
    @staticmethod
    def build_admin_menu() -> List[List[Button]]:
        """构建管理员菜单键盘"""
        return [
            [
                Button.inline("👥 用户管理", b"admin:users"),
                Button.inline("📊 系统统计", b"admin:system_stats")
            ],
            [
                Button.inline("📢 发送广播", b"admin:broadcast"),
                Button.inline("📋 查看日志", b"admin:logs")
            ],
            [
                Button.inline("🔧 系统设置", b"admin:system_settings"),
                Button.inline("🔄 重启服务", b"admin:restart")
            ],
            [
                Button.inline("◀️ 返回主菜单", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_accounts_menu() -> List[List[Button]]:
        """构建账号管理菜单键盘"""
        return [
            [
                Button.inline("📋 账号列表", b"accounts:list"),
                Button.inline("➕ 添加账号", b"accounts:add")
            ],
            [
                Button.inline("✅ 启用账号", b"accounts:enable"),
                Button.inline("❌ 禁用账号", b"accounts:disable")
            ],
            [
                Button.inline("✏️ 编辑账号", b"accounts:edit"),
                Button.inline("🗑️ 删除账号", b"accounts:delete")
            ],
            [
                Button.inline("🔄 测试签到", b"accounts:test"),
                Button.inline("📊 签到记录", b"accounts:history")
            ],
            [
                Button.inline("◀️ 返回主菜单", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_add_account_keyboard() -> List[List[Button]]:
        """构建添加账号类型选择键盘"""
        return [
            [
                Button.inline("🌐 网页签到", b"add:web"),
                Button.inline("📱 APP签到", b"add:app")
            ],
            [
                Button.inline("🔗 API签到", b"add:api"),
                Button.inline("🤖 自定义", b"add:custom")
            ],
            [
                Button.inline("
                text = btn_config.get("text", "")
                callback_data = btn_config.get("callback_data", "")
                url = btn_config.get("url")
                
                if url:
                    button_row.append(Button.url(text, url))
                else:
                    button_row.append(Button.inline(text, callback_data.encode()))
            
            if button_row:
                keyboard.append(button_row)
        
        return keyboard
    
    @staticmethod
    def build_account_status_keyboard(account_id: int, is_enabled: bool) -> List[List[Button]]:
        """构建账号状态切换键盘"""
        if is_enabled:
            status_button = Button.inline("❌ 禁用账号", f"account_disable:{account_id}".encode())
        else:
            status_button = Button.inline("✅ 启用账号", f"account_enable:{account_id}".encode())
        
        return [
            [status_button],
            [
                Button.inline("◀️ 返回", f"account_detail:{account_id}".encode())
            ]
        ]
    
    @staticmethod
    def build_export_keyboard() -> List[List[Button]]:
        """构建导出选项键盘"""
        return [
            [
                Button.inline("📊 导出统计数据", b"export:stats"),
                Button.inline("📋 导出账号列表", b"export:accounts")
            ],
            [
                Button.inline("📝 导出签到日志", b"export:logs"),
                Button.inline("⚙️ 导出配置", b"export:config")
            ],
            [
                Button.inline("📦 导出全部数据", b"export:all")
            ],
            [
                Button.inline("◀️ 返回", b"action:main_menu")
            ]
        ]


class DynamicKeyboard:
    """动态键盘生成器"""
    
    @staticmethod
    def build_account_selection(accounts: List[Dict[str, Any]], action: str, page: int = 0) -> List[List[Button]]:
        """构建账号选择键盘"""
        keyboard = []
        per_page = 8
        
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_accounts = accounts[start_idx:end_idx]
        
        # 每行2个按钮
        for i in range(0, len(page_accounts), 2):
            row = []
            for j in range(2):
                if i + j < len(page_accounts):
                    account = page_accounts[i + j]
                    text = f"{'✅' if account.get('enabled') else '❌'} {account['name'][:15]}"
                    callback_data = f"{action}:{account['id']}"
                    row.append(Button.inline(text, callback_data.encode()))
            keyboard.append(row)
        
        # 分页导航
        total_pages = (len(accounts) + per_page - 1) // per_page
        if total_pages > 1:
            nav_row = []
            if page > 0:
                nav_row.append(Button.inline("⬅️", f"{action}_page:{page-1}".encode()))
            nav_row.append(Button.inline(f"{page+1}/{total_pages}", b"noop"))
            if page < total_pages - 1:
                nav_row.append(Button.inline("➡️", f"{action}_page:{page+1}".encode()))
            keyboard.append(nav_row)
        
        # 返回按钮
        keyboard.append([Button.inline("◀️ 返回", b"action:accounts")])
        
        return keyboard
    
    @staticmethod
    def build_checkin_options(accounts: List[Dict[str, Any]]) -> List[List[Button]]:
        """构建签到选项键盘"""
        keyboard = []
        
        if accounts:
            keyboard.extend([
                [
                    Button.inline("🔄 全部签到", b"checkin:all"),
                    Button.inline("✅ 仅启用账号", b"checkin:enabled_only")
                ],
                [
                    Button.inline("🎯 选择账号", b"checkin:select"),
                    Button.inline("❌ 仅失败账号", b"checkin:failed_only")
                ]
            ])
        else:
            keyboard.append([
                Button.inline("➕ 先添加账号", b"action:add_account")
            ])
        
        keyboard.append([
            Button.inline("◀️ 返回主菜单", b"action:main_menu")
        ])
        
        return keyboard
    
    @staticmethod
    def build_filter_keyboard(current_filter: str = "all") -> List[List[Button]]:
        """构建过滤器键盘"""
        filters = [
            ("全部", "all", "📋"),
            ("已启用", "enabled", "✅"),
            ("已禁用", "disabled", "❌"),
            ("成功", "success", "🟢"),
            ("失败", "failed", "🔴")
        ]
        
        keyboard = []
        for i in range(0, len(filters), 2):
            row = []
            for j in range(2):
                if i + j < len(filters):
                    name, filter_type, emoji = filters[i + j]
                    text = f"{emoji} {name}"
                    if filter_type == current_filter:
                        text = f"• {text}"
                    
                    row.append(Button.inline(text, f"filter:{filter_type}".encode()))
            keyboard.append(row)
        
        return keyboard


class ContextualKeyboard:
    """上下文相关键盘生成器"""
    
    @staticmethod
    def build_context_menu(context: str, item_id: str = None) -> List[List[Button]]:
        """根据上下文构建菜单"""
        keyboard_map = {
            "account": KeyboardBuilder.build_account_detail_keyboard,
            "settings": KeyboardBuilder.build_settings_menu,
            "admin": KeyboardBuilder.build_admin_menu,
            "help": KeyboardBuilder.build_help_keyboard
        }
        
        builder = keyboard_map.get(context)
        if builder and item_id:
            return builder(int(item_id))
        elif builder:
            return builder()
        else:
            return KeyboardBuilder.build_main_menu()
    
    @staticmethod
    def build_smart_keyboard(user_data: Dict[str, Any]) -> List[List[Button]]:
        """根据用户数据构建智能键盘"""
        keyboard = []
        
        # 根据用户的账号数量决定显示什么
        account_count = user_data.get('account_count', 0)
        
        if account_count == 0:
            # 新用户，引导添加账号
            keyboard = [
                [
                    Button.inline("🚀 快速开始", b"help:quickstart"),
                    Button.inline("➕ 添加第一个账号", b"action:add_account")
                ],
                [
                    Button.inline("❓ 使用帮助", b"action:help")
                ]
            ]
        elif account_count < 3:
            # 少量账号，建议添加更多
            keyboard = [
                [
                    Button.inline("🔄 签到", b"action:checkin_now"),
                    Button.inline("📊 状态", b"action:status")
                ],
                [
                    Button.inline("📋 我的账号", b"action:accounts"),
                    Button.inline("➕ 添加更多", b"action:add_account")
                ]
            ]
        else:
            # 正常用户
            keyboard = KeyboardBuilder.build_main_menu()
        
        return keyboard


class KeyboardUtils:
    """键盘工具类"""
    
    @staticmethod
    def add_navigation(keyboard: List[List[Button]], back_action: str = None, home_action: str = "action:main_menu") -> List[List[Button]]:
        """为键盘添加导航按钮"""
        nav_row = []
        
        if back_action:
            nav_row.append(Button.inline("◀️ 返回", back_action.encode()))
        
        nav_row.append(Button.inline("🏠 主菜单", home_action.encode()))
        
        keyboard.append(nav_row)
        return keyboard
    
    @staticmethod
    def add_help_button(keyboard: List[List[Button]]) -> List[List[Button]]:
        """为键盘添加帮助按钮"""
        keyboard.append([Button.inline("❓ 帮助", b"action:help")])
        return keyboard
    
    @staticmethod
    def limit_text_length(text: str, max_length: int = 30) -> str:
        """限制按钮文本长度"""
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."
    
    @staticmethod
    def format_button_text(text: str, status: str = None, count: int = None) -> str:
        """格式化按钮文本"""
        formatted = text
        
        if status:
            status_emoji = {
                'active': '✅',
                'inactive': '❌',
                'pending': '⏳',
                'error': '🔴',
                'success': '🟢'
            }
            formatted = f"{status_emoji.get(status, '')} {formatted}"
        
        if count is not None:
            formatted += f" ({count})"
        
        return formatted
    
    @staticmethod
    def create_url_button(text: str, url: str) -> Button:
        """创建URL按钮"""
        return Button.url(text, url)
    
    @staticmethod
    def create_callback_button(text: str, callback_data: str) -> Button:
        """创建回调按钮"""
        return Button.inline(text, callback_data.encode())
    
    @staticmethod
    def validate_keyboard(keyboard: List[List[Button]]) -> bool:
        """验证键盘格式"""
        if not keyboard or not isinstance(keyboard, list):
            return False
        
        for row in keyboard:
            if not isinstance(row, list):
                return False
            
            if len(row) > 8:  # Telegram限制每行最多8个按钮
                return False
            
            for button in row:
                if not isinstance(button, Button):
                    return False
        
        return True


# 全局键盘实例
keyboard_builder = KeyboardBuilder()
dynamic_keyboard = DynamicKeyboard()
contextual_keyboard = ContextualKeyboard()
keyboard_utils = KeyboardUtils()
