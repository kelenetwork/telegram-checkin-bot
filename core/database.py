"""
数据库管理模块
处理所有数据库操作
"""

import sqlite3
import asyncio
import aiosqlite
import logging
import json
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path
import traceback

logger = logging.getLogger(__name__)

class Database:
    """数据库管理类"""
    
    def __init__(self, db_path: str = "data/bot_database.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._connection_pool = {}
        self._lock = asyncio.Lock()
        
    async def initialize(self):
        """初始化数据库"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
                await db.commit()
            logger.info("✅ 数据库初始化完成")
        except Exception as e:
            logger.error(f"❌ 数据库初始化失败: {e}")
            raise
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """创建数据库表"""
        
        # 用户表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT DEFAULT 'zh',
                is_active BOOLEAN DEFAULT 1,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT DEFAULT '{}'
            )
        """)
        
        # 账号表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                account_type TEXT NOT NULL,
                session_data TEXT,
                phone_number TEXT,
                username TEXT,
                api_id INTEGER,
                api_hash TEXT,
                is_enabled BOOLEAN DEFAULT 1,
                status TEXT DEFAULT 'inactive',
                last_checkin TIMESTAMP,
                last_success TIMESTAMP,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                config TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # 签到记录表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS checkin_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                account_id INTEGER NOT NULL,
                checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN NOT NULL,
                points_earned INTEGER DEFAULT 0,
                error_message TEXT,
                response_data TEXT,
                duration_ms INTEGER,
                ip_address TEXT,
                user_agent TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (account_id) REFERENCES accounts (id)
            )
        """)
        
        # 任务表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                priority INTEGER DEFAULT 2,
                scheduled_time TIMESTAMP,
                created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_time TIMESTAMP,
                completed_time TIMESTAMP,
                retry_count INTEGER DEFAULT 0,
                max_retries INTEGER DEFAULT 3,
                error_message TEXT,
                result TEXT,
                data TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # 设置表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, setting_key),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # 统计表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                total_accounts INTEGER DEFAULT 0,
                successful_checkins INTEGER DEFAULT 0,
                failed_checkins INTEGER DEFAULT 0,
                total_points INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, date),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        # 系统日志表
        await db.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                level TEXT NOT NULL,
                message TEXT NOT NULL,
                module TEXT,
                function TEXT,
                user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                extra_data TEXT
            )
        """)
        
        # 创建索引
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status)",
            "CREATE INDEX IF NOT EXISTS idx_checkin_logs_user_id ON checkin_logs(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_checkin_logs_account_id ON checkin_logs(account_id)",
            "CREATE INDEX IF NOT EXISTS idx_checkin_logs_time ON checkin_logs(checkin_time)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
            "CREATE INDEX IF NOT EXISTS idx_statistics_user_date ON statistics(user_id, date)",
            "CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)"
        ]
        
        for index_sql in indexes:
            await db.execute(index_sql)
    
    async def get_connection(self) -> aiosqlite.Connection:
        """获取数据库连接"""
        return await aiosqlite.connect(self.db_path)
    
    # ==================== 用户管理 ====================
    
    async def add_user(self, user_data: Dict[str, Any]) -> bool:
        """添加或更新用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO users 
                    (user_id, username, first_name, last_name, language_code, last_activity)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    user_data['user_id'],
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    user_data.get('language_code', 'zh')
                ))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"添加用户失败: {e}")
            return False
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM users WHERE user_id = ?", (user_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [description[0] for description in cursor.description]
                        user_data = dict(zip(columns, row))
                        user_data['settings'] = json.loads(user_data.get('settings', '{}'))
                        return user_data
                    return None
        except Exception as e:
            logger.error(f"获取用户失败: {e}")
            return None
    
    async def update_user_activity(self, user_id: int) -> bool:
        """更新用户活动时间"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"更新用户活动时间失败: {e}")
            return False
    
    async def get_all_users(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """获取所有用户"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT * FROM users"
                if active_only:
                    query += " WHERE is_active = 1"
                
                async with db.execute(query) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    users = []
                    for row in rows:
                        user_data = dict(zip(columns, row))
                        user_data['settings'] = json.loads(user_data.get('settings', '{}'))
                        users.append(user_data)
                    
                    return users
        except Exception as e:
            logger.error(f"获取所有用户失败: {e}")
            return []
    
    # ==================== 账号管理 ====================
    
    async def add_account(self, account_data: Dict[str, Any]) -> Optional[int]:
        """添加账号"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO accounts 
                    (user_id, name, account_type, session_data, phone_number, username, 
                     api_id, api_hash, config)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_data['user_id'],
                    account_data['name'],
                    account_data['account_type'],
                    account_data.get('session_data'),
                    account_data.get('phone_number'),
                    account_data.get('username'),
                    account_data.get('api_id'),
                    account_data.get('api_hash'),
                    json.dumps(account_data.get('config', {}))
                ))
                
                account_id = cursor.lastrowid
                await db.commit()
                
                logger.info(f"账号添加成功: {account_data['name']} (ID: {account_id})")
                return account_id
                
        except Exception as e:
            logger.error(f"添加账号失败: {e}")
            return None
    
    async def get_user_accounts(self, user_id: int, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """获取用户账号列表"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT * FROM accounts WHERE user_id = ?"
                params = [user_id]
                
                if enabled_only:
                    query += " AND is_enabled = 1"
                
                query += " ORDER BY created_at DESC"
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    accounts = []
                    for row in rows:
                        account_data = dict(zip(columns, row))
                        account_data['config'] = json.loads(account_data.get('config', '{}'))
                        accounts.append(account_data)
                    
                    return accounts
                    
        except Exception as e:
            logger.error(f"获取用户账号失败: {e}")
            return []
    
    async def get_account(self, account_id: int) -> Optional[Dict[str, Any]]:
        """获取单个账号信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT * FROM accounts WHERE id = ?", (account_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        columns = [description[0] for description in cursor.description]
                        account_data = dict(zip(columns, row))
                        account_data['config'] = json.loads(account_data.get('config', '{}'))
                        return account_data
                    return None
        except Exception as e:
            logger.error(f"获取账号失败: {e}")
            return None
    
    async def update_account(self, account_id: int, updates: Dict[str, Any]) -> bool:
        """更新账号信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 构建更新语句
                set_clauses = []
                params = []
                
                for key, value in updates.items():
                    if key == 'config':
                        value = json.dumps(value)
                    set_clauses.append(f"{key} = ?")
                    params.append(value)
                
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                params.append(account_id)
                
                query = f"UPDATE accounts SET {', '.join(set_clauses)} WHERE id = ?"
                
                await db.execute(query, params)
                await db.commit()
                
                return True
                
        except Exception as e:
            logger.error(f"更新账号失败: {e}")
            return False
    
    async def delete_account(self, account_id: int) -> bool:
        """删除账号"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
                await db.commit()
                
                # 删除相关的签到记录
                await db.execute("DELETE FROM checkin_logs WHERE account_id = ?", (account_id,))
                await db.commit()
                
                logger.info(f"账号已删除: {account_id}")
                return True
                
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
            return False
    
    # ==================== 签到记录管理 ====================
    
    async def add_checkin_log(self, log_data: Dict[str, Any]) -> Optional[int]:
        """添加签到记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO checkin_logs 
                    (user_id, account_id, success, points_earned, error_message, 
                     response_data, duration_ms, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_data['user_id'],
                    log_data['account_id'],
                    log_data['success'],
                    log_data.get('points_earned', 0),
                    log_data.get('error_message'),
                    json.dumps(log_data.get('response_data', {})),
                    log_data.get('duration_ms', 0),
                    log_data.get('ip_address'),
                    log_data.get('user_agent')
                ))
                
                log_id = cursor.lastrowid
                await db.commit()
                
                # 更新账号统计信息
                await self._update_account_stats(log_data['account_id'], log_data['success'], 
                                                log_data.get('points_earned', 0))
                
                return log_id
                
        except Exception as e:
            logger.error(f"添加签到记录失败: {e}")
            return None
    
    async def get_checkin_logs(self, user_id: int = None, account_id: int = None,
                              start_date: datetime = None, end_date: datetime = None,
                              limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """获取签到记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = """
                    SELECT cl.*, a.name as account_name, a.account_type 
                    FROM checkin_logs cl 
                    LEFT JOIN accounts a ON cl.account_id = a.id 
                    WHERE 1=1
                """
                params = []
                
                if user_id:
                    query += " AND cl.user_id = ?"
                    params.append(user_id)
                
                if account_id:
                    query += " AND cl.account_id = ?"
                    params.append(account_id)
                
                if start_date:
                    query += " AND cl.checkin_time >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND cl.checkin_time <= ?"
                    params.append(end_date.isoformat())
                
                query += " ORDER BY cl.checkin_time DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    logs = []
                    for row in rows:
                        log_data = dict(zip(columns, row))
                        log_data['response_data'] = json.loads(log_data.get('response_data', '{}'))
                        logs.append(log_data)
                    
                    return logs
                    
        except Exception as e:
            logger.error(f"获取签到记录失败: {e}")
            return []
    
    async def get_today_checkin_status(self, user_id: int) -> Dict[str, Any]:
        """获取今日签到状态"""
        try:
            today = datetime.now().date()
            start_time = datetime.combine(today, datetime.min.time())
            end_time = datetime.combine(today, datetime.max.time())
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取今日签到统计
                async with db.execute("""
                    SELECT 
                        COUNT(*) as total_checkins,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_checkins,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_checkins,
                        SUM(points_earned) as total_points
                    FROM checkin_logs 
                    WHERE user_id = ? AND checkin_time BETWEEN ? AND ?
                """, (user_id, start_time, end_time)) as cursor:
                    stats_row = await cursor.fetchone()
                
                # 获取账号签到状态
                async with db.execute("""
                    SELECT 
                        a.id, a.name, a.account_type,
                        cl.success, cl.checkin_time, cl.points_earned, cl.error_message
                    FROM accounts a
                    LEFT JOIN checkin_logs cl ON a.id = cl.account_id 
                        AND DATE(cl.checkin_time) = DATE(?)
                    WHERE a.user_id = ? AND a.is_enabled = 1
                    ORDER BY a.name
                """, (datetime.now(), user_id)) as cursor:
                    account_rows = await cursor.fetchall()
                
                account_status = []
                for row in account_rows:
                    account_status.append({
                        'account_id': row[0],
                        'account_name': row[1],
                        'account_type': row[2],
                        'checked_in': row[3] is not None,
                        'success': bool(row[3]) if row[3] is not None else None,
                        'checkin_time': row[4],
                        'points_earned': row[5] or 0,
                        'error_message': row[6]
                    })
                
                return {
                    'total_checkins': stats_row[0] or 0,
                    'successful_checkins': stats_row[1] or 0,
                    'failed_checkins': stats_row[2] or 0,
                    'total_points': stats_row[3] or 0,
                    'accounts': account_status
                }
                
        except Exception as e:
            logger.error(f"获取今日签到状态失败: {e}")
            return {
                'total_checkins': 0,
                'successful_checkins': 0,
                'failed_checkins': 0,
                'total_points': 0,
                'accounts': []
            }
    
    async def _update_account_stats(self, account_id: int, success: bool, points: int):
        """更新账号统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                if success:
                    await db.execute("""
                        UPDATE accounts 
                        SET success_count = success_count + 1,
                            total_points = total_points + ?,
                            last_success = CURRENT_TIMESTAMP,
                            last_checkin = CURRENT_TIMESTAMP,
                            status = 'active'
                        WHERE id = ?
                    """, (points, account_id))
                else:
                    await db.execute("""
                        UPDATE accounts 
                        SET fail_count = fail_count + 1,
                            last_checkin = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (account_id,))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"更新账号统计失败: {e}")
    
    # ==================== 任务管理 ====================
    
    async def add_task(self, task_data: Dict[str, Any]) -> Optional[int]:
        """添加任务"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO tasks 
                    (task_id, user_id, task_type, status, priority, scheduled_time, 
                     max_retries, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_data['task_id'],
                    task_data['user_id'],
                    task_data['task_type'],
                    task_data.get('status', 'pending'),
                    task_data.get('priority', 2),
                    task_data.get('scheduled_time'),
                    task_data.get('max_retries', 3),
                    json.dumps(task_data.get('data', {}))
                ))
                
                task_id = cursor.lastrowid
                await db.commit()
                return task_id
                
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return None
    
    async def update_task(self, task_data: Dict[str, Any]) -> bool:
        """更新任务"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE tasks 
                    SET status = ?, started_time = ?, completed_time = ?, 
                        retry_count = ?, error_message = ?, result = ?
                    WHERE task_id = ?
                """, (
                    task_data['status'],
                    task_data.get('started_time'),
                    task_data.get('completed_time'),
                    task_data.get('retry_count', 0),
                    task_data.get('error_message'),
                    json.dumps(task_data.get('result', {})),
                    task_data['task_id']
                ))
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"更新任务失败: {e}")
            return False
    
    async def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """获取待处理任务"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT * FROM tasks 
                    WHERE status IN ('pending', 'failed') 
                        AND retry_count < max_retries
                    ORDER BY priority DESC, created_time ASC
                """) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    tasks = []
                    for row in rows:
                        task_data = dict(zip(columns, row))
                        task_data['data'] = json.loads(task_data.get('data', '{}'))
                        task_data['result'] = json.loads(task_data.get('result', '{}'))
                        tasks.append(task_data)
                    
                    return tasks
                    
        except Exception as e:
            logger.error(f"获取待处理任务失败: {e}")
            return []
    
    # ==================== 设置管理 ====================
    
    async def get_user_setting(self, user_id: int, key: str) -> Optional[str]:
        """获取用户设置"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT setting_value FROM user_settings WHERE user_id = ? AND setting_key = ?",
                    (user_id, key)
                ) as cursor:
                    row = await cursor.fetchone()
                    return row[0] if row else None
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return None
    
    async def set_user_setting(self, user_id: int, key: str, value: str) -> bool:
        """设置用户设置"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO user_settings 
                    (user_id, setting_key, setting_value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (user_id, key, value))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"设置用户设置失败: {e}")
            return False
    
    async def get_user_settings(self, user_id: int) -> Dict[str, str]:
        """获取用户所有设置"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    "SELECT setting_key, setting_value FROM user_settings WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    rows = await cursor.fetchall()
                    return {row[0]: row[1] for row in rows}
        except Exception as e:
            logger.error(f"获取用户设置失败: {e}")
            return {}
    
    # ==================== 统计管理 ====================
    
    async def update_daily_stats(self, user_id: int, date: datetime.date = None):
        """更新每日统计"""
        if date is None:
            date = datetime.now().date()
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 计算当日统计数据
                start_time = datetime.combine(date, datetime.min.time())
                end_time = datetime.combine(date, datetime.max.time())
                
                async with db.execute("""
                    SELECT 
                        COUNT(DISTINCT account_id) as total_accounts,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_checkins,
                        SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_checkins,
                        SUM(points_earned) as total_points
                    FROM checkin_logs 
                    WHERE user_id = ? AND checkin_time BETWEEN ? AND ?
                """, (user_id, start_time, end_time)) as cursor:
                    stats = await cursor.fetchone()
                
                # 更新或插入统计记录
                await db.execute("""
                    INSERT OR REPLACE INTO statistics 
                    (user_id, date, total_accounts, successful_checkins, failed_checkins, total_points)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    user_id, date,
                    stats[0] or 0, stats[1] or 0, stats[2] or 0, stats[3] or 0
                ))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"更新每日统计失败: {e}")
    
    async def get_user_statistics(self, user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """获取用户统计数据"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                end_date = datetime.now().date()
                start_date = end_date - timedelta(days=days)
                
                async with db.execute("""
                    SELECT * FROM statistics 
                    WHERE user_id = ? AND date BETWEEN ? AND ?
                    ORDER BY date DESC
                """, (user_id, start_date, end_date)) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    return [dict(zip(columns,
                    return [dict(zip(columns, row)) for row in rows]
                    
        except Exception as e:
            logger.error(f"获取用户统计失败: {e}")
            return []
    
    # ==================== 系统日志管理 ====================
    
    async def add_system_log(self, level: str, message: str, module: str = None,
                           function: str = None, user_id: int = None, 
                           extra_data: Dict[str, Any] = None):
        """添加系统日志"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO system_logs 
                    (level, message, module, function, user_id, extra_data)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    level, message, module, function, user_id,
                    json.dumps(extra_data) if extra_data else None
                ))
                await db.commit()
        except Exception as e:
            logger.error(f"添加系统日志失败: {e}")
    
    async def get_system_logs(self, level: str = None, limit: int = 100,
                            offset: int = 0) -> List[Dict[str, Any]]:
        """获取系统日志"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = "SELECT * FROM system_logs"
                params = []
                
                if level:
                    query += " WHERE level = ?"
                    params.append(level)
                
                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    columns = [description[0] for description in cursor.description]
                    
                    logs = []
                    for row in rows:
                        log_data = dict(zip(columns, row))
                        if log_data.get('extra_data'):
                            log_data['extra_data'] = json.loads(log_data['extra_data'])
                        logs.append(log_data)
                    
                    return logs
                    
        except Exception as e:
            logger.error(f"获取系统日志失败: {e}")
            return []
    
    # ==================== 数据库维护 ====================
    
    async def cleanup_old_data(self, days: int = 30):
        """清理旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                # 清理旧的签到记录
                result1 = await db.execute(
                    "DELETE FROM checkin_logs WHERE checkin_time < ?",
                    (cutoff_date,)
                )
                
                # 清理旧的任务记录
                result2 = await db.execute(
                    "DELETE FROM tasks WHERE completed_time < ? AND status IN ('completed', 'failed')",
                    (cutoff_date,)
                )
                
                # 清理旧的系统日志
                result3 = await db.execute(
                    "DELETE FROM system_logs WHERE timestamp < ?",
                    (cutoff_date,)
                )
                
                await db.commit()
                
                total_cleaned = (result1.rowcount or 0) + (result2.rowcount or 0) + (result3.rowcount or 0)
                logger.info(f"清理了 {total_cleaned} 条旧记录")
                
                return total_cleaned
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return 0
    
    async def vacuum_database(self):
        """优化数据库"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("VACUUM")
                await db.commit()
            logger.info("数据库优化完成")
        except Exception as e:
            logger.error(f"数据库优化失败: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                stats = {}
                
                # 表记录数统计
                tables = ['users', 'accounts', 'checkin_logs', 'tasks', 
                         'user_settings', 'statistics', 'system_logs']
                
                for table in tables:
                    async with db.execute(f"SELECT COUNT(*) FROM {table}") as cursor:
                        count = await cursor.fetchone()
                        stats[f"{table}_count"] = count[0]
                
                # 数据库文件大小
                stats['database_size'] = self.db_path.stat().st_size
                
                # 最近活动
                async with db.execute(
                    "SELECT MAX(last_activity) FROM users"
                ) as cursor:
                    last_activity = await cursor.fetchone()
                    stats['last_user_activity'] = last_activity[0]
                
                return stats
                
        except Exception as e:
            logger.error(f"获取数据库统计失败: {e}")
            return {}
    
    async def backup_database(self, backup_path: str = None) -> bool:
        """备份数据库"""
        try:
            if backup_path is None:
                backup_dir = Path("backups")
                backup_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = backup_dir / f"database_backup_{timestamp}.db"
            
            # 复制数据库文件
            import shutil
            shutil.copy2(self.db_path, backup_path)
            
            logger.info(f"数据库备份完成: {backup_path}")
            return True
            
        except Exception as e:
            logger.error(f"数据库备份失败: {e}")
            return False
    
    async def close(self):
        """关闭数据库连接"""
        # 清理连接池
        for conn in self._connection_pool.values():
            try:
                await conn.close()
            except:
                pass
        
        self._connection_pool.clear()
        logger.info("数据库连接已关闭")

