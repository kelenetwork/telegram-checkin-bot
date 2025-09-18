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
            [
                Button.inline("◀️ 取消", b"action:cancel")
            ]
        ]
    
    @staticmethod
    def build_settings_menu() -> List[List[Button]]:
        """构建设置菜单键盘"""
        return [
            [
                Button.inline("⏰ 签到时间", b"settings:time"),
                Button.inline("🔔 通知设置", b"settings:notifications")
            ],
            [
                Button.inline("🌐 语言设置", b"settings:language"),
                Button.inline("🎨 主题设置", b"settings:theme")
            ],
            [
                Button.inline("🔐 安全设置", b"settings:security"),
                Button.inline("📊 数据设置", b"settings:data")
            ],
            [
                Button.inline("🔄 重置设置", b"settings:reset"),
                Button.inline("💾 导出数据", b"settings:export")
            ],
            [
                Button.inline("◀️ 返回主菜单", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_notification_settings() -> List[List[Button]]:
        """构建通知设置键盘"""
        return [
            [
                Button.inline("✅ 签到成功", b"notif:success"),
                Button.inline("❌ 签到失败", b"notif:failed")
            ],
            [
                Button.inline("📊 每日统计", b"notif:daily_stats"),
                Button.inline("📈 周报告", b"notif:weekly_report")
            ],
            [
                Button.inline("⚠️ 系统警告", b"notif:warnings"),
                Button.inline("🔔 全部通知", b"notif:all")
            ],
            [
                Button.inline("🔕 关闭通知", b"notif:disable"),
                Button.inline("◀️ 返回", b"settings:back")
            ]
        ]
    
    @staticmethod
    def build_account_list_keyboard(accounts: List[Dict], page: int = 0, per_page: int = 5) -> List[List[Button]]:
        """构建账号列表键盘"""
        buttons = []
        
        # 计算分页
        start_idx = page * per_page
        end_idx = start_idx + per_page
        page_accounts = accounts[start_idx:end_idx]
        
        # 添加账号按钮
        for account in page_accounts:
            status_emoji = "✅" if account.get('enabled', True) else "❌"
            name = account.get('name', 'Unknown')[:20]  # 限制长度
            
            buttons.append([
                Button.inline(
                    f"{status_emoji} {name}",
                    f"account:view:{account['id']}".encode()
                )
            ])
        
        # 分页按钮
        nav_buttons = []
        total_pages = (len(accounts) + per_page - 1) // per_page
        
        if page > 0:
            nav_buttons.append(Button.inline("⬅️ 上页", f"accounts:page:{page-1}".encode()))
        
        if page < total_pages - 1:
            nav_buttons.append(Button.inline("➡️ 下页", f"accounts:page:{page+1}".encode()))
        
        if nav_buttons:
            buttons.append(nav_buttons)
        
        # 返回按钮
        buttons.append([Button.inline("◀️ 返回", b"accounts:back")])
        
        return buttons
    
    @staticmethod
    def build_account_detail_keyboard(account_id: int) -> List[List[Button]]:
        """构建账号详情键盘"""
        return [
            [
                Button.inline("🔄 立即签到", f"account:checkin:{account_id}".encode()),
                Button.inline("✏️ 编辑", f"account:edit:{account_id}".encode())
            ],
            [
                Button.inline("📊 签到记录", f"account:history:{account_id}".encode()),
                Button.inline("🔧 测试连接", f"account:test:{account_id}".encode())
            ],
            [
                Button.inline("✅ 启用", f"account:enable:{account_id}".encode()),
                Button.inline("❌ 禁用", f"account:disable:{account_id}".encode())
            ],
            [
                Button.inline("🗑️ 删除", f"account:delete:{account_id}".encode()),
                Button.inline("◀️ 返回", b"accounts:list")
            ]
        ]
    
    @staticmethod
    def build_edit_account_keyboard(account_id: int) -> List[List[Button]]:
        """构建编辑账号键盘"""
        return [
            [
                Button.inline("📝 名称", f"edit:name:{account_id}".encode()),
                Button.inline("🔗 网址", f"edit:url:{account_id}".encode())
            ],
            [
                Button.inline("👤 用户名", f"edit:username:{account_id}".encode()),
                Button.inline("🔒 密码", f"edit:password:{account_id}".encode())
            ],
            [
                Button.inline("⚙️ 高级设置", f"edit:advanced:{account_id}".encode()),
                Button.inline("🎯 签到参数", f"edit:params:{account_id}".encode())
            ],
            [
                Button.inline("💾 保存", f"edit:save:{account_id}".encode()),
                Button.inline("◀️ 返回", f"account:view:{account_id}".encode())
            ]
        ]
    
    @staticmethod
    def build_confirm_keyboard(action: str, target_id: str = "") -> List[List[Button]]:
        """构建确认操作键盘"""
        return [
            [
                Button.inline("✅ 确认", f"confirm:{action}:{target_id}".encode()),
                Button.inline("❌ 取消", b"action:cancel")
            ]
        ]
    
    @staticmethod
    def build_delete_confirm_keyboard(account_id: int) -> List[List[Button]]:
        """构建删除确认键盘"""
        return [
            [
                Button.inline("🗑️ 确认删除", f"delete:confirm:{account_id}".encode()),
                Button.inline("❌ 取消", f"account:view:{account_id}".encode())
            ]
        ]
    
    @staticmethod
    def build_add_account_confirm_keyboard() -> List[List[Button]]:
        """构建添加账号确认键盘"""
        return [
            [
                Button.inline("✅ 确认添加", b"add:confirm"),
                Button.inline("✏️ 修改", b"add:edit")
            ],
            [
                Button.inline("❌ 取消", b"add:cancel")
            ]
        ]
    
    @staticmethod
    def build_checkin_keyboard() -> List[List[Button]]:
        """构建签到操作键盘"""
        return [
            [
                Button.inline("🔄 全部签到", b"checkin:all"),
                Button.inline("✅ 仅启用账号", b"checkin:enabled")
            ],
            [
                Button.inline("🎯 选择账号", b"checkin:select"),
                Button.inline("⚡ 快速签到", b"checkin:quick")
            ],
            [
                Button.inline("◀️ 返回主菜单", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_stats_keyboard() -> List[List[Button]]:
        """构建统计数据键盘"""
        return [
            [
                Button.inline("📊 今日统计", b"stats:today"),
                Button.inline("📈 本周统计", b"stats:week")
            ],
            [
                Button.inline("📅 本月统计", b"stats:month"),
                Button.inline("📆 历史统计", b"stats:history")
            ],
            [
                Button.inline("🏆 成功率排行", b"stats:ranking"),
                Button.inline("📋 详细报告", b"stats:detailed")
            ],
            [
                Button.inline("💾 导出数据", b"stats:export"),
                Button.inline("◀️ 返回主菜单", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_url_action_keyboard(url: str) -> List[List[Button]]:
        """构建URL操作键盘"""
        return [
            [
                Button.inline("➕ 添加为签到账号", f"url:add:{url}".encode()),
                Button.inline("🔍 检查网站", f"url:check:{url}".encode())
            ],
            [
                Button.inline("🌐 在浏览器打开", url=url),
                Button.inline("❌ 取消", b"action:cancel")
            ]
        ]
    
    @staticmethod
    def build_confirm_account_keyboard(json_data: str) -> List[List[Button]]:
        """构建确认账号信息键盘"""
        import base64
        encoded_data = base64.b64encode(json_data.encode()).decode()
        
        return [
            [
                Button.inline("✅ 确认添加", f"account:confirm:{encoded_data}".encode()),
                Button.inline("✏️ 修改信息", b"action:edit_json")
            ],
            [
                Button.inline("❌ 取消", b"action:cancel")
            ]
        ]
    
    @staticmethod
    def build_time_selection_keyboard() -> List[List[Button]]:
        """构建时间选择键盘"""
        return [
            [
                Button.inline("🌅 早上 8:00", b"time:08:00"),
                Button.inline("🌞 上午 10:00", b"time:10:00")
            ],
            [
                Button.inline("🌝 中午 12:00", b"time:12:00"),
                Button.inline("🌆 下午 15:00", b"time:15:00")
            ],
            [
                Button.inline("🌙 晚上 20:00", b"time:20:00"),
                Button.inline("🌃 深夜 23:00", b"time:23:00")
            ],
            [
                Button.inline("⌨️ 手动输入", b"time:custom"),
                Button.inline("◀️ 返回", b"settings:back")
            ]
        ]
    
    @staticmethod
    def build_logs_menu() -> List[List[Button]]:
        """构建日志菜单键盘"""
        return [
            [
                Button.inline("📝 全部日志", b"logs:all"),
                Button.inline("❌ 错误日志", b"logs:error")
            ],
            [
                Button.inline("⚠️ 警告日志", b"logs:warning"),
                Button.inline("📊 签到日志", b"logs:checkin")
            ],
            [
                Button.inline("🔄 刷新", b"logs:refresh"),
                Button.inline("🗑️ 清空日志", b"logs:clear")
            ],
            [
                Button.inline("💾 导出日志", b"logs:export"),
                Button.inline("◀️ 返回", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_broadcast_confirm_keyboard() -> List[List[Button]]:
        """构建广播确认键盘"""
        return [
            [
                Button.inline("📢 确认发送", b"broadcast:confirm"),
                Button.inline("✏️ 编辑消息", b"broadcast:edit")
            ],
            [
                Button.inline("❌ 取消", b"broadcast:cancel")
            ]
        ]
    
    @staticmethod
    def build_help_keyboard() -> List[List[Button]]:
        """构建帮助菜单键盘"""
        return [
            [
                Button.inline("🚀 快速开始", b"help:quick_start"),
                Button.inline("📋 命令列表", b"help:commands")
            ],
            [
                Button.inline("❓ 常见问题", b"help:faq"),
                Button.inline("🔧 故障排除", b"help:troubleshoot")
            ],
            [
                Button.inline("📞 联系支持", b"help:contact"),
                Button.inline("🌐 项目主页", url="https://github.com/your-repo")
            ],
            [
                Button.inline("◀️ 返回主菜单", b"action:main_menu")
            ]
        ]
    
    @staticmethod
    def build_pagination_keyboard(
        items: List[Dict], 
        page: int, 
        per_page: int, 
        callback_prefix: str
    ) -> List[List[Button]]:
        """构建通用分页键盘"""
        buttons = []
        
        # 计算分页信息
        total_pages = (len(items) + per_page - 1) // per_page
        start_idx = page * per_page
        end_idx = start_idx + per_page
        
        # 导航按钮
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(
                Button.inline("⬅️", f"{callback_prefix}:page:{page-1}".encode())
            )
        
        nav_buttons.append(
            Button.inline(f"{page+1}/{total_pages}", b"noop")
        )
        
        if page < total_pages - 1:
            nav_buttons.append(
                Button.inline("➡️", f"{callback_prefix}:page:{page+1}".encode())
            )
        
        if len(nav_buttons) > 1:
            buttons.append(nav_buttons)
        
        return buttons
    
    @staticmethod
    def build_dynamic_keyboard(config: List[Dict[str, Any]]) -> List[List[Button]]:
        """根据配置动态构建键盘"""
        buttons = []
        
        for row_config in config:
            row = []
            for button_config in row_config.get('buttons', []):
                button_type = button_config.get('type', 'callback')
                text = button_config.get('text', '')
                
                if button_type == 'callback':
                    data = button_config.get('data', '').encode()
                    row.append(Button.inline(text, data))
                elif button_type == 'url':
                    url = button_config.get('url', '')
                    row.append(Button.url(text, url))
                elif button_type == 'switch_inline':
                    query = button_config.get('query', '')
                    row.append(Button.switch_inline(text, query))
            
            if row:
                buttons.append(row)
        
        return buttons

