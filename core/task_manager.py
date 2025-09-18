"""
任务管理模块
管理自动签到任务的执行和调度
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime
"""
任务管理模块
管理自动签到任务的执行和调度
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import traceback
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"        # 等待中
    RUNNING = "running"        # 运行中
    COMPLETED = "completed"    # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"    # 已取消
    PAUSED = "paused"          # 暂停中

class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4

@dataclass
class Task:
    """任务数据类"""
    task_id: str
    user_id: int
    task_type: str
    data: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    scheduled_time: Optional[datetime] = None
    created_time: datetime = field(default_factory=datetime.now)
    started_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None

class TaskManager:
    """任务管理器"""
    
    def __init__(self, config: Dict[str, Any], bot_manager, database):
        self.config = config
        self.bot_manager = bot_manager
        self.database = database
        self.tasks = {}  # task_id -> Task
        self.task_queue = asyncio.PriorityQueue()
        self.running_tasks = {}  # task_id -> asyncio.Task
        self.max_concurrent_tasks = config.get('task_manager', {}).get('max_concurrent', 5)
        self.worker_tasks = []
        self.running = False
        
        # 任务执行器映射
        self.task_executors = {
            'checkin': self._execute_checkin_task,
            'account_verification': self._execute_verification_task,
            'data_backup': self._execute_backup_task,
            'report_generation': self._execute_report_task,
            'cleanup': self._execute_cleanup_task,
        }
    
    async def start(self):
        """启动任务管理器"""
        if self.running:
            return
        
        self.running = True
        logger.info("📋 启动任务管理器...")
        
        # 启动工作线程
        for i in range(self.max_concurrent_tasks):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.worker_tasks.append(worker)
        
        # 恢复未完成的任务
        await self._restore_pending_tasks()
        
        logger.info(f"✅ 任务管理器已启动，工作线程数: {len(self.worker_tasks)}")
    
    async def stop(self):
        """停止任务管理器"""
        if not self.running:
            return
        
        logger.info("⏹️ 停止任务管理器...")
        self.running = False
        
        # 取消所有运行中的任务
        for task_id, task in self.running_tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"取消任务: {task_id}")
        
        # 等待工作线程结束
        for worker in self.worker_tasks:
            worker.cancel()
        
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        
        logger.info("✅ 任务管理器已停止")
    
    async def add_task(self, user_id: int, task_type: str, data: Dict[str, Any] = None,
                      priority: TaskPriority = TaskPriority.NORMAL,
                      scheduled_time: datetime = None) -> str:
        """添加任务"""
        task_id = f"{task_type}_{user_id}_{int(datetime.now().timestamp())}"
        
        task = Task(
            task_id=task_id,
            user_id=user_id,
            task_type=task_type,
            data=data or {},
            priority=priority,
            scheduled_time=scheduled_time
        )
        
        self.tasks[task_id] = task
        
        # 如果是立即执行的任务，加入队列
        if scheduled_time is None or scheduled_time <= datetime.now():
            await self.task_queue.put((-priority.value, datetime.now(), task))
            logger.info(f"添加任务到队列: {task_id} (类型: {task_type})")
        else:
            logger.info(f"添加定时任务: {task_id} (执行时间: {scheduled_time})")
        
        return task_id
    
    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # 如果任务正在运行，取消协程
        if task_id in self.running_tasks:
            running_task = self.running_tasks[task_id]
            if not running_task.done():
                running_task.cancel()
                logger.info(f"取消运行中任务: {task_id}")
        
        # 更新任务状态
        task.status = TaskStatus.CANCELLED
        task.completed_time = datetime.now()
        
        await self._update_task_in_database(task)
        
        logger.info(f"任务已取消: {task_id}")
        return True
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        if task_id not in self.tasks:
            return None
        
        task = self.tasks[task_id]
        return {
            'task_id': task.task_id,
            'status': task.status.value,
            'priority': task.priority.value,
            'created_time': task.created_time.isoformat(),
            'started_time': task.started_time.isoformat() if task.started_time else None,
            'completed_time': task.completed_time.isoformat() if task.completed_time else None,
            'retry_count': task.retry_count,
            'error_message': task.error_message,
            'result': task.result
        }
    
    async def get_user_tasks(self, user_id: int, status: TaskStatus = None) -> List[Dict[str, Any]]:
        """获取用户任务列表"""
        user_tasks = []
        
        for task in self.tasks.values():
            if task.user_id == user_id:
                if status is None or task.status == status:
                    user_tasks.append(await self.get_task_status(task.task_id))
        
        return user_tasks
    
    async def retry_failed_tasks(self, user_id: int = None) -> int:
        """重试失败的任务"""
        retry_count = 0
        
        for task in self.tasks.values():
            if task.status == TaskStatus.FAILED:
                if user_id is None or task.user_id == user_id:
                    if task.retry_count < task.max_retries:
                        task.status = TaskStatus.PENDING
                        task.retry_count += 1
                        task.error_message = None
                        
                        await self.task_queue.put((-task.priority.value, datetime.now(), task))
                        retry_count += 1
                        logger.info(f"重试任务: {task.task_id} (第{task.retry_count}次)")
        
        return retry_count
    
    async def _worker(self, worker_name: str):
        """工作线程"""
        logger.info(f"启动工作线程: {worker_name}")
        
        while self.running:
            try:
                # 获取任务（带超时，避免无限等待）
                try:
                    _, _, task = await asyncio.wait_for(
                        self.task_queue.get(), timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue
                
                # 检查任务是否已被取消
                if task.status == TaskStatus.CANCELLED:
                    continue
                
                # 检查是否为定时任务且未到执行时间
                if task.scheduled_time and task.scheduled_time > datetime.now():
                    # 重新放回队列
                    await self.task_queue.put((-task.priority.value, task.scheduled_time, task))
                    await asyncio.sleep(1)  # 短暂等待
                    continue
                
                # 执行任务
                await self._execute_task(task, worker_name)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"工作线程 {worker_name} 发生错误: {e}")
                logger.error(traceback.format_exc())
        
        logger.info(f"工作线程停止: {worker_name}")
    
    async def _execute_task(self, task: Task, worker_name: str):
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.started_time = datetime.now()
        
        logger.info(f"[{worker_name}] 开始执行任务: {task.task_id}")
        
        try:
            # 获取任务执行器
            executor = self.task_executors.get(task.task_type)
            if not executor:
                raise ValueError(f"未知任务类型: {task.task_type}")
            
            # 创建任务协程
            task_coroutine = asyncio.create_task(executor(task))
            self.running_tasks[task.task_id] = task_coroutine
            
            # 执行任务
            result = await task_coroutine
            
            # 任务完成
            task.status = TaskStatus.COMPLETED
            task.result = result
            task.completed_time = datetime.now()
            
            logger.info(f"[{worker_name}] 任务完成: {task.task_id}")
            
        except asyncio.CancelledError:
            task.status = TaskStatus.CANCELLED
            task.completed_time = datetime.now()
            logger.info(f"[{worker_name}] 任务被取消: {task.task_id}")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_message = str(e)
            task.completed_time = datetime.now()
            
            logger.error(f"[{worker_name}] 任务执行失败: {task.task_id} - {e}")
            logger.error(traceback.format_exc())
            
            # 如果还有重试次数，重新加入队列
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.PENDING
                task.error_message = None
                
                # 延迟重试
                await asyncio.sleep(min(2 ** task.retry_count, 60))
                await self.task_queue.put((-task.priority.value, datetime.now(), task))
                
                logger.info(f"任务将重试: {task.task_id} (第{task.retry_count}次)")
        
        finally:
            # 清理运行中任务记录
            if task.task_id in self.running_tasks:
                del self.running_tasks[task.task_id]
            
            # 更新数据库
            await self._update_task_in_database(task)
    
    async def _execute_checkin_task(self, task: Task) -> Dict[str, Any]:
        """执行签到任务"""
        user_id = task.user_id
        account_ids = task.data.get('account_ids', [])
        
        if not account_ids:
            # 获取用户所有启用的账号
            from core.account_manager import AccountManager
            account_manager = AccountManager(self.config, self.database)
            accounts = await account_manager.get_user_accounts(user_id, enabled_only=True)
            account_ids = [acc['id'] for acc in accounts]
        
        if not account_ids:
            return {'success': False, 'error': '没有可用的账号'}
        
        results = []
        for account_id in account_ids:
            try:
                # 这里应该调用具体的签到逻辑
                # 为演示目的，使用模拟结果
                result = await self._perform_checkin(account_id)
                results.append(result)
                
                # 避免频率限制
                await asyncio.sleep(1)
                
            except Exception as e:
                results.append({
                    'account_id': account_id,
                    'success': False,
                    'error': str(e)
                })
        
        return {
            'success': True,
            'results': results,
            'total_accounts': len(account_ids),
            'successful_accounts': len([r for r in results if r.get('success')])
        }
    
    async def _perform_checkin(self, account_id: int) -> Dict[str, Any]:
        """执行具体的签到操作（待实现）"""
        # 这里应该实现具体的签到逻辑
        # 现在返回模拟结果
        return {
            'account_id': account_id,
            'success': True,
            'points': 10,
            'message': '签到成功'
        }
    
    async def _execute_verification_task(self, task: Task) -> Dict[str, Any]:
        """执行账号验证任务"""
        # 实现账号验证逻辑
        return {'success': True, 'message': '验证完成'}
    
    async def _execute_backup_task(self, task: Task) -> Dict[str, Any]:
        """执行数据备份任务"""
        # 实现数据备份逻辑
        return {'success': True, 'message': '备份完成'}
    
    async def _execute_report_task(self, task: Task) -> Dict[str, Any]:
        """执行报告生成任务"""
        # 实现报告生成逻辑
        return {'success': True, 'message': '报告生成完成'}
    
    async def _execute_cleanup_task(self, task: Task) -> Dict[str, Any]:
        """执行清理任务"""
        # 实现数据清理逻辑
        return {'success': True, 'message': '清理完成'}
    
    async def _restore_pending_tasks(self):
        """恢复未完成的任务"""
        try:
            # 从数据库恢复未完成的任务
            # 这里需要实现
    async def _restore_pending_tasks(self):
        """恢复未完成的任务"""
        try:
            # 从数据库恢复未完成的任务
            # 这里需要实现数据库查询逻辑
            restored_count = 0
            
            # 模拟恢复逻辑（实际应从数据库查询）
            # pending_tasks = await self.database.get_pending_tasks()
            # for task_data in pending_tasks:
            #     task = Task(**task_data)
            #     self.tasks[task.task_id] = task
            #     await self.task_queue.put((-task.priority.value, datetime.now(), task))
            #     restored_count += 1
            
            if restored_count > 0:
                logger.info(f"恢复了 {restored_count} 个未完成任务")
            
        except Exception as e:
            logger.error(f"恢复任务失败: {e}")
    
    async def _update_task_in_database(self, task: Task):
        """更新任务到数据库"""
        try:
            # 实现数据库更新逻辑
            task_data = {
                'task_id': task.task_id,
                'user_id': task.user_id,
                'task_type': task.task_type,
                'status': task.status.value,
                'priority': task.priority.value,
                'created_time': task.created_time,
                'started_time': task.started_time,
                'completed_time': task.completed_time,
                'retry_count': task.retry_count,
                'error_message': task.error_message,
                'result': task.result,
                'data': task.data
            }
            
            # await self.database.update_task(task_data)
            
        except Exception as e:
            logger.error(f"更新任务到数据库失败: {e}")
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取任务统计信息"""
        stats = {
            'total_tasks': len(self.tasks),
            'pending_tasks': 0,
            'running_tasks': len(self.running_tasks),
            'completed_tasks': 0,
            'failed_tasks': 0,
            'cancelled_tasks': 0,
            'queue_size': self.task_queue.qsize(),
            'worker_count': len(self.worker_tasks)
        }
        
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                stats['pending_tasks'] += 1
            elif task.status == TaskStatus.COMPLETED:
                stats['completed_tasks'] += 1
            elif task.status == TaskStatus.FAILED:
                stats['failed_tasks'] += 1
            elif task.status == TaskStatus.CANCELLED:
                stats['cancelled_tasks'] += 1
        
        return stats
    
    async def cleanup_old_tasks(self, days: int = 7):
        """清理旧任务"""
        cutoff_time = datetime.now() - timedelta(days=days)
        cleaned_count = 0
        
        tasks_to_remove = []
        for task_id, task in self.tasks.items():
            if (task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and
                task.completed_time and task.completed_time < cutoff_time):
                tasks_to_remove.append(task_id)
        
        for task_id in tasks_to_remove:
            del self.tasks[task_id]
            cleaned_count += 1
        
        logger.info(f"清理了 {cleaned_count} 个旧任务")
        return cleaned_count

