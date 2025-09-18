"""
任务调度器
管理定时任务和异步任务调度
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime, timedelta, time
from dataclasses import dataclass
import traceback
from croniter import croniter
import pytz

from .database import Database
from .account_manager import AccountManager
from .message_sender import MessageSender

logger = logging.getLogger(__name__)

@dataclass
class ScheduledTask:
    """调度任务数据类"""
    task_id: str
    name: str
    cron_expression: str
    callback: Callable
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    max_errors: int = 5
    timeout: int = 300  # 5分钟超时
    user_id: Optional[int] = None
    kwargs: Dict[str, Any] = None

class Scheduler:
    """任务调度器类"""
    
    def __init__(self, database: Database, account_manager: AccountManager, 
                 message_sender: MessageSender):
        self.database = database
        self.account_manager = account_manager  
        self.message_sender = message_sender
        
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.scheduler_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # 时区设置
        self.timezone = pytz.timezone('Asia/Shanghai')
    
    async def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行中")
            return
        
        self.is_running = True
        self.scheduler_task = asyncio.create_task(self._scheduler_loop())
        
        # 添加默认任务
        await self._setup_default_tasks()
        
        logger.info("✅ 任务调度器已启动")
    
    async def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止调度器循环
        if self.scheduler_task:
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # 取消所有运行中的任务
        for task in self.running_tasks.values():
            task.cancel()
        
        # 等待所有任务完成
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        self.running_tasks.clear()
        logger.info("✅ 任务调度器已停止")
    
    async def _scheduler_loop(self):
        """调度器主循环"""
        try:
            while self.is_running:
                try:
                    await self._check_and_run_tasks()
                    await asyncio.sleep(10)  # 每10秒检查一次
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"调度器循环错误: {e}")
                    await asyncio.sleep(30)  # 出错后延长等待时间
        except asyncio.CancelledError:
            logger.info("调度器循环被取消")
        except Exception as e:
            logger.error(f"调度器循环异常退出: {e}")
    
    async def _check_and_run_tasks(self):
        """检查并运行到期的任务"""
        now = datetime.now(self.timezone)
        
        for task in self.scheduled_tasks.values():
            if not task.enabled:
                continue
            
            # 更新下次运行时间
            if task.next_run is None:
                task.next_run = self._get_next_run_time(task.cron_expression, now)
                continue
            
            # 检查是否需要运行
            if now >= task.next_run and task.task_id not in self.running_tasks:
                # 检查错误次数
                if task.error_count >= task.max_errors:
                    logger.warning(f"任务 {task.name} 错误次数过多，已禁用")
                    task.enabled = False
                    continue
                
                # 创建任务
                async_task = asyncio.create_task(
                    self._run_task(task)
                )
                self.running_tasks[task.task_id] = async_task
                
                # 更新下次运行时间
                task.next_run = self._get_next_run_time(task.cron_expression, now)
        
        # 清理已完成的任务
        completed_tasks = [
            task_id for task_id, task in self.running_tasks.items() 
            if task.done()
        ]
        
        for task_id in completed_tasks:
            del self.running_tasks[task_id]
    
    async def _run_task(self, scheduled_task: ScheduledTask):
        """运行单个任务"""
        start_time = datetime.now()
        
        try:
            logger.info(f"开始执行任务: {scheduled_task.name}")
            
            # 设置超时
            kwargs = scheduled_task.kwargs or {}
            
            await asyncio.wait_for(
                scheduled_task.callback(**kwargs),
                timeout=scheduled_task.timeout
            )
            
            # 更新成功统计
            scheduled_task.last_run = start_time
            scheduled_task.run_count += 1
            scheduled_task.error_count = 0  # 重置错误计数
            
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"任务 {scheduled_task.name} 执行成功，耗时 {duration:.2f} 秒")
            
        except asyncio.TimeoutError:
            logger.error(f"任务 {scheduled_task.name} 执行超时")
            scheduled_task.error_count += 1
            
        except Exception as e:
            logger.error(f"任务 {scheduled_task.name} 执行失败: {e}")
            logger.error(traceback.format_exc())
            scheduled_task.error_count += 1
            
            # 发送错误通知
            if scheduled_task.user_id:
                try:
                    await self.message_sender.send_error_notification(
                        scheduled_task.user_id,
                        f"定时任务执行失败",
                        f"任务: {scheduled_task.name}\n错误: {str(e)}"
                    )
                except:
                    pass
    
    def _get_next_run_time(self, cron_expression: str, base_time: datetime) -> datetime:
        """获取下次运行时间"""
        try:
            cron = croniter(cron_expression, base_time)
            next_time = cron.get_next(datetime)
            return self.timezone.localize(next_time.replace(tzinfo=None))
        except Exception as e:
            logger.error(f"解析cron表达式失败 {cron_expression}: {e}")
            # 默认返回1小时后
            return base_time + timedelta(hours=1)
    
    async def _setup_default_tasks(self):
        """设置默认任务"""
        # 全局自动签到任务
        await self.add_task(
            task_id="global_auto_checkin",
            name="全局自动签到",
            cron_expression="0 8 * * *",  # 每天8点
            callback=self._global_auto_checkin_task
        )
        
        # 数据库清理任务
        await self.add_task(
            task_id="database_cleanup",
            name="数据库清理",
            cron_expression="0 2 * * 0",  # 每周日2点
            callback=self._database_cleanup_task
        )
        
        # 每日统计更新任务
        await self.add_task(
            task_id="daily_stats_update",
            name="每日统计更新",
            cron_expression="5 0 * * *",  # 每天0点5分
            callback=self._daily_stats_update_task
        )
        
        # 发送每日报告任务
        await self.add_task(
            task_id="daily_report",
            name="每日报告",
            cron_expression="0 21 * * *",  # 每天21点
            callback=self._daily_report_task
        )
    
       async def add_task(self, task_id: str, name: str, cron_expression: str,
                      callback: Callable, enabled: bool = True,
                      user_id: int = None, timeout: int = 300,
                      max_errors: int = 5, **kwargs) -> bool:
        """添加调度任务"""
        try:
            # 验证cron表达式
            try:
                croniter(cron_expression)
            except Exception as e:
                logger.error(f"无效的cron表达式 {cron_expression}: {e}")
                return False
            
            task = ScheduledTask(
                task_id=task_id,
                name=name,
                cron_expression=cron_expression,
                callback=callback,
                enabled=enabled,
                user_id=user_id,
                timeout=timeout,
                max_errors=max_errors,
                kwargs=kwargs
            )
            
            # 计算下次运行时间
            now = datetime.now(self.timezone)
            task.next_run = self._get_next_run_time(cron_expression, now)
            
            self.scheduled_tasks[task_id] = task
            
            logger.info(f"任务已添加: {name} (下次运行: {task.next_run})")
            return True
            
        except Exception as e:
            logger.error(f"添加任务失败: {e}")
            return False
    
    async def remove_task(self, task_id: str) -> bool:
        """移除调度任务"""
        try:
            if task_id in self.scheduled_tasks:
                del self.scheduled_tasks[task_id]
                
                # 取消运行中的任务
                if task_id in self.running_tasks:
                    self.running_tasks[task_id].cancel()
                    del self.running_tasks[task_id]
                
                logger.info(f"任务已移除: {task_id}")
                return True
            else:
                logger.warning(f"任务不存在: {task_id}")
                return False
                
        except Exception as e:
            logger.error(f"移除任务失败: {e}")
            return False
    
    async def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].enabled = True
            self.scheduled_tasks[task_id].error_count = 0  # 重置错误计数
            logger.info(f"任务已启用: {task_id}")
            return True
        return False
    
    async def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].enabled = False
            
            # 取消运行中的任务
            if task_id in self.running_tasks:
                self.running_tasks[task_id].cancel()
                del self.running_tasks[task_id]
            
            logger.info(f"任务已禁用: {task_id}")
            return True
        return False
    
    async def get_task_status(self, task_id: str = None) -> Dict[str, Any]:
        """获取任务状态"""
        if task_id:
            task = self.scheduled_tasks.get(task_id)
            if not task:
                return {}
            
            return {
                'task_id': task.task_id,
                'name': task.name,
                'enabled': task.enabled,
                'last_run': task.last_run.isoformat() if task.last_run else None,
                'next_run': task.next_run.isoformat() if task.next_run else None,
                'run_count': task.run_count,
                'error_count': task.error_count,
                'is_running': task_id in self.running_tasks,
                'cron_expression': task.cron_expression
            }
        else:
            # 返回所有任务状态
            return {
                'scheduler_running': self.is_running,
                'total_tasks': len(self.scheduled_tasks),
                'running_tasks': len(self.running_tasks),
                'tasks': [
                    {
                        'task_id': task.task_id,
                        'name': task.name,
                        'enabled': task.enabled,
                        'last_run': task.last_run.isoformat() if task.last_run else None,
                        'next_run': task.next_run.isoformat() if task.next_run else None,
                        'run_count': task.run_count,
                        'error_count': task.error_count,
                        'is_running': task_id in self.running_tasks
                    }
                    for task_id, task in self.scheduled_tasks.items()
                ]
            }
    
    # ==================== 默认任务实现 ====================
    
    async def _global_auto_checkin_task(self):
        """全局自动签到任务"""
        logger.info("开始执行全局自动签到任务")
        
        try:
            # 获取所有启用自动签到的用户
            users = await self.database.get_all_users(active_only=True)
            
            for user in users:
                try:
                    # 检查用户是否启用了自动签到
                    auto_checkin = await self.database.get_user_setting(
                        user['user_id'], 'auto_checkin'
                    )
                    
                    if auto_checkin != 'true':
                        continue
                    
                    # 获取用户账号
                    accounts = await self.database.get_user_accounts(
                        user['user_id'], enabled_only=True
                    )
                    
                    if not accounts:
                        continue
                    
                    # 检查今天是否已经签到
                    today_status = await self.database.get_today_checkin_status(
                        user['user_id']
                    )
                    
                    unchecked_accounts = [
                        acc for acc in accounts 
                        if not any(
                            status['account_id'] == acc['id'] and status['checked_in'] 
                            for status in today_status['accounts']
                        )
                    ]
                    
                    if not unchecked_accounts:
                        logger.info(f"用户 {user['user_id']} 今日已全部签到完成")
                        continue
                    
                    # 执行自动签到
                    logger.info(f"为用户 {user['user_id']} 执行自动签到，账号数量: {len(unchecked_accounts)}")
                    
                    checkin_results = await self.account_manager.batch_checkin(
                        user['user_id'], 
                        [acc['id'] for acc in unchecked_accounts]
                    )
                    
                    # 发送签到结果通知
                    await self._send_checkin_notification(
                        user['user_id'], checkin_results
                    )
                    
                    # 添加延迟避免频繁操作
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"用户 {user.get('user_id')} 自动签到失败: {e}")
                    continue
            
            logger.info("全局自动签到任务完成")
            
        except Exception as e:
            logger.error(f"全局自动签到任务执行失败: {e}")
            raise
    
    async def _database_cleanup_task(self):
        """数据库清理任务"""
        logger.info("开始执行数据库清理任务")
        
        try:
            # 清理30天前的旧数据
            cleaned_count = await self.database.cleanup_old_data(days=30)
            
            # 优化数据库
            await self.database.vacuum_database()
            
            # 备份数据库
            backup_success = await self.database.backup_database()
            
            logger.info(f"数据库清理完成: 清理记录 {cleaned_count} 条，备份: {'成功' if backup_success else '失败'}")
            
        except Exception as e:
            logger.error(f"数据库清理任务失败: {e}")
            raise
    
    async def _daily_stats_update_task(self):
        """每日统计更新任务"""
        logger.info("开始执行每日统计更新任务")
        
        try:
            users = await self.database.get_all_users(active_only=True)
            yesterday = datetime.now().date() - timedelta(days=1)
            
            for user in users:
                try:
                    await self.database.update_daily_stats(
                        user['user_id'], yesterday
                    )
                except Exception as e:
                    logger.error(f"更新用户 {user['user_id']} 统计失败: {e}")
                    continue
            
            logger.info("每日统计更新完成")
            
        except Exception as e:
            logger.error(f"每日统计更新任务失败: {e}")
            raise
    
    async def _daily_report_task(self):
        """每日报告任务"""
        logger.info("开始执行每日报告任务")
        
        try:
            users = await self.database.get_all_users(active_only=True)
            
            for user in users:
                try:
                    # 检查用户是否启用了每日报告
                    daily_report = await self.database.get_user_setting(
                        user['user_id'], 'daily_report'
                    )
                    
                    if daily_report != 'true':
                        continue
                    
                    # 生成今日报告
                    report = await self._generate_daily_report(user['user_id'])
                    
                    if report:
                        # 发送报告
                        await self.message_sender.send_daily_report(
                            user['user_id'], report
                        )
                    
                except Exception as e:
                    logger.error(f"为用户 {user['user_id']} 生成每日报告失败: {e}")
                    continue
            
            logger.info("每日报告任务完成")
            
        except Exception as e:
            logger.error(f"每日报告任务失败: {e}")
            raise
    
    async def _generate_daily_report(self, user_id: int) -> Optional[Dict[str, Any]]:
        """生成每日报告"""
        try:
            # 获取今日签到状态
            today_status = await self.database.get_today_checkin_status(user_id)
            
            # 获取用户账号数量
            accounts = await self.database.get_user_accounts(user_id, enabled_only=True)
            
            if not accounts:
                return None
            
            report = {
                'date': datetime.now().strftime('%Y-%m-%d'),
                'total_accounts': len(accounts),
                'total_checkins': today_status['total_checkins'],
                'successful_checkins': today_status['successful_checkins'],
                'failed_checkins': today_status['failed_checkins'],
                'total_points': today_status['total_points'],
                'success_rate': (
                    today_status['successful_checkins'] / len(accounts) * 100 
                    if accounts else 0
                ),
                'account_details': today_status['accounts']
            }
            
            return report
            
        except Exception as e:
            logger.error(f"生成每日报告失败: {e}")
            return None
    
    async def _send_checkin_notification(self, user_id: int, results: List[Dict[str, Any]]):
        """发送签到结果通知"""
        try:
            if not results:
                return
            
            success_count = sum(1 for r in results if r.get('success'))
            total_count = len(results)
            total_points = sum(r.get('points', 0) for r in results if r.get('success'))
            
            # 构建通知消息
            message = f"🎯 自动签到完成\n\n"
            message += f"✅ 成功: {success_count}/{total_count}\n"
            message += f"💎 获得积分: {total_points}\n\n"
            
            # 显示失败的账号
            failed_accounts = [r for r in results if not r.get('success')]
            if failed_accounts:
                message += "❌ 签到失败:\n"
                for acc in failed_accounts[:3]:  # 最多显示3个失败账号
                    message += f"• {acc.get('account_name', 'Unknown')}: {acc.get('error', 'Unknown error')}\n"
                
                if len(failed_accounts) > 3:
                    message += f"• ...及其他 {len(failed_accounts) - 3} 个账号\n"
            
            await self.message_sender.send_notification(user_id, message)
            
        except Exception as e:
            logger.error(f"发送签到通知失败: {e}")
    
    # ==================== 用户定制任务 ====================
    
    async def add_user_checkin_task(self, user_id: int, schedule_time: str) -> bool:
        """为用户添加定制签到任务"""
        try:
            task_id = f"user_checkin_{user_id}"
            
            # 验证时间格式 (HH:MM)
            try:
                hour, minute = map(int, schedule_time.split(':'))
                if not (0 <= hour <= 23 and 0 <= minute <= 59):
                    raise ValueError("时间范围无效")
            except ValueError:
                logger.error(f"无效的时间格式: {schedule_time}")
                return False
            
            # 构建cron表达式 (每天指定时间)
            cron_expression = f"{minute} {hour} * * *"
            
            return await self.add_task(
                task_id=task_id,
                name=f"用户 {user_id} 定制签到",
                cron_expression=cron_expression,
                callback=self._user_checkin_task,
                user_id=user_id,
                target_user_id=user_id
            )
            
        except Exception as e:
            logger.error(f"添加用户签到任务失败: {e}")
            return False
    
    async def remove_user_checkin_task(self, user_id: int) -> bool:
        """移除用户定制签到任务"""
        task_id = f"user_checkin_{user_id}"
        return await self.remove_task(task_id)
    
    async def _user_checkin_task(self, target_user_id: int):
        """用户定制签到任务"""
        logger.info(f"执行用户 {target_user_id} 的定制签到任务")
        
        try:
            # 获取用户启用的账号
            accounts = await self.database.get_user_accounts(
                target_user_id, enabled_only=True
            )
            
                       if not accounts:
                logger.info(f"用户 {target_user_id} 没有启用的账号")
                return
            
            # 检查今日签到状态
            today_status = await self.database.get_today_checkin_status(target_user_id)
            
            unchecked_accounts = [
                acc for acc in accounts 
                if not any(
                    status['account_id'] == acc['id'] and status['checked_in'] 
                    for status in today_status['accounts']
                )
            ]
            
            if not unchecked_accounts:
                logger.info(f"用户 {target_user_id} 今日已全部签到完成")
                return
            
            # 执行签到
            logger.info(f"为用户 {target_user_id} 执行签到，账号数量: {len(unchecked_accounts)}")
            
            checkin_results = await self.account_manager.batch_checkin(
                target_user_id,
                [acc['id'] for acc in unchecked_accounts]
            )
            
            # 发送通知
            await self._send_checkin_notification(target_user_id, checkin_results)
            
        except Exception as e:
            logger.error(f"用户 {target_user_id} 定制签到任务失败: {e}")
            raise


# 全局调度器实例
scheduler = None

async def get_scheduler(database: Database = None, account_manager: AccountManager = None,
                       message_sender: MessageSender = None) -> Scheduler:
    """获取调度器实例"""
    global scheduler
    
    if scheduler is None:
        if not all([database, account_manager, message_sender]):
            raise ValueError("首次创建调度器需要提供所有依赖组件")
        scheduler = Scheduler(database, account_manager, message_sender)
    
    return scheduler

                
