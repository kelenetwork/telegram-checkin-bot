"""
账号管理器
管理用户账号的增删改查和签到操作
"""

import asyncio
import logging
import aiohttp
import time
import json
import random
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from urllib.parse import urlencode, quote
import hashlib
import hmac
import base64

from .database import Database
from .config import Config

logger = logging.getLogger(__name__)

class AccountManager:
    """账号管理器类"""
    
    def __init__(self, database: Database, config: Config):
        self.database = database
        self.config = config
        
        # HTTP客户端设置
        self.timeout = aiohttp.ClientTimeout(total=30)
        self.max_concurrent = 5  # 最大并发数
        
        # 签到间隔配置
        self.checkin_interval = (3, 8)  # 3-8秒随机间隔
        
        # 用户代理池
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        
        # 支持的账号类型及其配置
        self.account_types = {
            'bilibili': {
                'name': 'B站',
                'checkin_url': 'https://api.bilibili.com/x/web-interface/nav',
                'login_url': 'https://passport.bilibili.com/x/passport-login/web/login',
                'required_fields': ['cookies'],
                'optional_fields': ['csrf_token']
            },
            'aliyundrive': {
                'name': '阿里云盘',
                'checkin_url': 'https://member.aliyundrive.com/v1/activity/sign_in_list',
                'required_fields': ['refresh_token'],
                'optional_fields': ['access_token']
            },
            'baidu_tieba': {
                'name': '百度贴吧',
                'checkin_url': 'http://tieba.baidu.com/sign/add',
                'required_fields': ['cookies', 'tbs'],
                'optional_fields': []
            },
            'jd': {
                'name': '京东',
                'checkin_url': 'https://api.m.jd.com/client.action',
                'required_fields': ['cookies'],
                'optional_fields': []
            },
            'v2ex': {
                'name': 'V2EX',
                'checkin_url': 'https://www.v2ex.com/mission/daily',
                'required_fields': ['cookies'],
                'optional_fields': ['once_token']
            }
        }
    
    # ==================== 账号基础操作 ====================
    
    async def add_account(self, user_id: int, account_data: Dict[str, Any]) -> Optional[int]:
        """添加账号"""
        try:
            account_type = account_data.get('account_type')
            if account_type not in self.account_types:
                logger.error(f"不支持的账号类型: {account_type}")
                return None
            
            # 验证必需字段
            type_config = self.account_types[account_type]
            required_fields = type_config['required_fields']
            
            for field in required_fields:
                if not account_data.get(field):
                    logger.error(f"缺少必需字段: {field}")
                    return None
            
            # 测试账号有效性
            is_valid, error_msg = await self._test_account(account_data)
            if not is_valid:
                logger.error(f"账号测试失败: {error_msg}")
                return None
            
            # 保存到数据库
            account_id = await self.database.add_account(account_data)
            
            if account_id:
                logger.info(f"账号添加成功: {account_data.get('name')} (ID: {account_id})")
                
                # 记录系统日志
                await self.database.add_system_log(
                    'info', f"用户添加账号: {account_data.get('name')}", 
                    'account_manager', 'add_account', user_id,
                    {'account_id': account_id, 'account_type': account_type}
                )
            
            return account_id
            
        except Exception as e:
            logger.error(f"添加账号失败: {e}")
            return None
    
    async def update_account(self, account_id: int, account_data: Dict[str, Any]) -> bool:
        """更新账号"""
        try:
            # 获取原账号信息
            original_account = await self.database.get_account(account_id)
            if not original_account:
                logger.error(f"账号不存在: {account_id}")
                return False
            
            # 如果更新了认证信息，需要重新测试
            auth_fields = ['cookies', 'token', 'refresh_token', 'access_token']
            auth_updated = any(
                field in account_data and account_data[field] != original_account.get(field)
                for field in auth_fields
            )
            
            if auth_updated:
                # 合并数据进行测试
                test_data = original_account.copy()
                test_data.update(account_data)
                
                is_valid, error_msg = await self._test_account(test_data)
                if not is_valid:
                    logger.error(f"账号更新测试失败: {error_msg}")
                    return False
            
            # 更新数据库
            success = await self.database.update_account(account_id, account_data)
            
            if success:
                logger.info(f"账号更新成功: {account_id}")
                
                # 记录系统日志
                await self.database.add_system_log(
                    'info', f"账号信息已更新", 'account_manager', 'update_account',
                    original_account.get('user_id'),
                    {'account_id': account_id, 'updated_fields': list(account_data.keys())}
                )
            
            return success
            
        except Exception as e:
            logger.error(f"更新账号失败: {e}")
            return False
    
    async def delete_account(self, account_id: int) -> bool:
        """删除账号"""
        try:
            # 获取账号信息用于日志记录
            account = await self.database.get_account(account_id)
            if not account:
                logger.error(f"账号不存在: {account_id}")
                return False
            
            success = await self.database.delete_account(account_id)
            
            if success:
                logger.info(f"账号删除成功: {account.get('name')} (ID: {account_id})")
                
                # 记录系统日志
                await self.database.add_system_log(
                    'info', f"账号已删除: {account.get('name')}", 
                    'account_manager', 'delete_account', account.get('user_id'),
                    {'account_id': account_id, 'account_name': account.get('name')}
                )
            
            return success
            
        except Exception as e:
            logger.error(f"删除账号失败: {e}")
            return False
    
    async def _test_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str]:
        """测试账号有效性"""
        account_type = account_data.get('account_type')
        
        try:
            if account_type == 'bilibili':
                return await self._test_bilibili_account(account_data)
            elif account_type == 'aliyundrive':
                return await self._test_aliyundrive_account(account_data)
            elif account_type == 'baidu_tieba':
                return await self._test_tieba_account(account_data)
            elif account_type == 'jd':
                return await self._test_jd_account(account_data)
            elif account_type == 'v2ex':
                return await self._test_v2ex_account(account_data)
            else:
                return False, f"不支持的账号类型: {account_type}"
                
        except Exception as e:
            logger.error(f"测试账号异常: {e}")
            return False, f"测试异常: {str(e)}"
    
    # ==================== 签到操作 ====================
    
    async def single_checkin(self, account_id: int) -> Dict[str, Any]:
        """单个账号签到"""
        start_time = time.time()
        
        try:
            # 获取账号信息
            account = await self.database.get_account(account_id)
            if not account:
                return {
                    'success': False,
                    'account_id': account_id,
                    'error': '账号不存在'
                }
            
            if not account.get('is_enabled'):
                return {
                    'success': False,
                    'account_id': account_id,
                    'account_name': account.get('name'),
                    'error': '账号已禁用'
                }
            
            # 执行签到
            account_type = account.get('account_type')
            
            if account_type == 'bilibili':
                result = await self._bilibili_checkin(account)
            elif account_type == 'aliyundrive':
                result = await self._aliyundrive_checkin(account)
            elif account_type == 'baidu_tieba':
                result = await self._tieba_checkin(account)
            elif account_type == 'jd':
                result = await self._jd_checkin(account)
            elif account_type == 'v2ex':
                result = await self._v2ex_checkin(account)
            else:
                result = {
                    'success': False,
                    'error': f'不支持的账号类型: {account_type}'
                }
            
            # 添加基础信息
            result.update({
                'account_id': account_id,
                'account_name': account.get('name'),
                'account_type': account_type,
                'duration_ms': int((time.time() - start_time) * 1000)
            })
            
            # 记录签到日志
            log_data = {
                'user_id': account.get('user_id'),
                'account_id': account_id,
                'success': result.get('success', False),
                'points_earned': result.get('points', 0),
                'error_message': result.get('error'),
                'response_data': result.get('response_data', {}),
                'duration_ms': result['duration_ms'],
                'ip_address': result.get('ip_address'),
                'user_agent': result.get('user_agent')
            }
            
            await self.database.add_checkin_log(log_data)
            
            return result
            
        except Exception as e:
            logger.error(f"账号 {account_id} 签到异常: {e}")
            return {
                'success': False,
                'account_id': account_id,
                'error': f'签到异常: {str(e)}',
                'duration_ms': int((time.time() - start_time) * 1000)
            }
    
    async def batch_checkin(self, user_id: int, account_ids: List[int] = None) -> List[Dict[str, Any]]:
        """批量签到"""
        try:
            # 如果未指定账号ID，获取用户所有启用的账号
            if account_ids is None:
                accounts = await self.database.get_user_accounts(user_id, enabled_only=True)
                account_ids = [acc['id'] for acc in accounts]
            
            if not account_ids:
                logger.info(f"用户 {user_id} 没有需要签到的账号")
                return []
            
            logger.info(f"开始批量签到，用户: {user_id}，账号数量: {len(account_ids)}")
            
            # 创建信号量限制并发数
            semaphore = asyncio.Semaphore(self.max_concurrent)
            
                        async def checkin_with_semaphore(account_id: int):
                async with semaphore:
                    # 添加随机延迟，避免请求过于频繁
                    if len(account_ids) > 1:
                        delay = random.uniform(*self.checkin_interval)
                        await asyncio.sleep(delay)
                    
                    return await self.single_checkin(account_id)
            
            # 并发执行签到
            tasks = [checkin_with_semaphore(account_id) for account_id in account_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed_results.append({
                        'success': False,
                        'account_id': account_ids[i],
                        'error': f'执行异常: {str(result)}'
                    })
                else:
                    processed_results.append(result)
            
            # 统计结果
            success_count = sum(1 for r in processed_results if r.get('success'))
            total_points = sum(r.get('points', 0) for r in processed_results if r.get('success'))
            
            logger.info(f"批量签到完成，成功: {success_count}/{len(account_ids)}，获得积分: {total_points}")
            
            return processed_results
            
        except Exception as e:
            logger.error(f"批量签到失败: {e}")
            return []
    
    # ==================== 各平台签到实现 ====================
    
    async def _bilibili_checkin(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """B站签到"""
        try:
            cookies_str = account.get('cookies', '')
            if not cookies_str:
                return {'success': False, 'error': 'Cookies为空'}
            
            # 解析cookies
            cookies = self._parse_cookies(cookies_str)
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://www.bilibili.com/',
                'Origin': 'https://www.bilibili.com'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 1. 获取用户信息
                async with session.get(
                    'https://api.bilibili.com/x/web-interface/nav',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return {'success': False, 'error': f'获取用户信息失败: {resp.status}'}
                    
                    nav_data = await resp.json()
                    if nav_data.get('code') != 0:
                        return {'success': False, 'error': f'用户信息错误: {nav_data.get("message")}'}
                    
                    user_info = nav_data.get('data', {})
                    if not user_info.get('isLogin'):
                        return {'success': False, 'error': 'Cookie已失效，请重新登录'}
                
                # 2. 执行签到
                async with session.post(
                    'https://api.bilibili.com/x/web-interface/coin/add',
                    cookies=cookies,
                    headers=headers,
                    data={'csrf': cookies.get('bili_jct', '')}
                ) as resp:
                    checkin_data = await resp.json()
                    
                    if checkin_data.get('code') == 0:
                        return {
                            'success': True,
                            'points': 5,  # B站签到默认经验值
                            'message': '签到成功',
                            'response_data': checkin_data
                        }
                    else:
                        return {
                            'success': False,
                            'error': checkin_data.get('message', '签到失败'),
                            'response_data': checkin_data
                        }
                        
        except Exception as e:
            logger.error(f"B站签到异常: {e}")
            return {'success': False, 'error': f'签到异常: {str(e)}'}
    
    async def _aliyundrive_checkin(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """阿里云盘签到"""
        try:
            refresh_token = account.get('refresh_token', '')
            access_token = account.get('access_token', '')
            
            if not refresh_token:
                return {'success': False, 'error': 'refresh_token为空'}
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Content-Type': 'application/json',
                'Origin': 'https://www.aliyundrive.com',
                'Referer': 'https://www.aliyundrive.com/'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 1. 刷新access_token（如果需要）
                if not access_token:
                    async with session.post(
                        'https://auth.aliyundrive.com/v2/account/token',
                        json={'refresh_token': refresh_token, 'grant_type': 'refresh_token'},
                        headers=headers
                    ) as resp:
                        if resp.status != 200:
                            return {'success': False, 'error': f'刷新token失败: {resp.status}'}
                        
                        token_data = await resp.json()
                        access_token = token_data.get('access_token')
                        if not access_token:
                            return {'success': False, 'error': 'refresh_token已失效'}
                
                # 2. 签到
                headers['Authorization'] = f'Bearer {access_token}'
                
                async with session.post(
                    'https://member.aliyundrive.com/v1/activity/sign_in_list',
                    json={'isReward': False},
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return {'success': False, 'error': f'签到请求失败: {resp.status}'}
                    
                    checkin_data = await resp.json()
                    
                    if checkin_data.get('success'):
                        # 获取签到奖励信息
                        reward_info = checkin_data.get('result', {})
                        return {
                            'success': True,
                            'points': reward_info.get('signInCount', 1),
                            'message': '签到成功',
                            'response_data': checkin_data
                        }
                    else:
                        return {
                            'success': False,
                            'error': checkin_data.get('message', '签到失败'),
                            'response_data': checkin_data
                        }
                        
        except Exception as e:
            logger.error(f"阿里云盘签到异常: {e}")
            return {'success': False, 'error': f'签到异常: {str(e)}'}
    
    async def _tieba_checkin(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """百度贴吧签到"""
        try:
            cookies_str = account.get('cookies', '')
            tbs = account.get('tbs', '')
            
            if not cookies_str:
                return {'success': False, 'error': 'Cookies为空'}
            
            cookies = self._parse_cookies(cookies_str)
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://tieba.baidu.com/',
                'Origin': 'https://tieba.baidu.com'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 1. 获取关注的贴吧列表
                async with session.get(
                    'https://tieba.baidu.com/f/like/mylike',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return {'success': False, 'error': f'获取贴吧列表失败: {resp.status}'}
                    
                    # 解析关注的贴吧（简化实现，实际需要解析HTML）
                    # 这里假设已经获取到贴吧列表
                    tieba_list = ['python', 'programming']  # 示例
                
                # 2. 执行签到
                success_count = 0
                total_points = 0
                
                for tieba_name in tieba_list[:5]:  # 限制最多签到5个贴吧
                    sign_data = {
                        'ie': 'utf-8',
                        'kw': tieba_name,
                        'tbs': tbs
                    }
                    
                    async with session.post(
                        'https://tieba.baidu.com/sign/add',
                        data=sign_data,
                        cookies=cookies,
                        headers=headers
                    ) as resp:
                        if resp.status == 200:
                            result = await resp.json()
                            if result.get('no') == 0:
                                success_count += 1
                                total_points += 1
                    
                    await asyncio.sleep(1)  # 避免频繁请求
                
                if success_count > 0:
                    return {
                        'success': True,
                        'points': total_points,
                        'message': f'签到成功 {success_count} 个贴吧'
                    }
                else:
                    return {'success': False, 'error': '所有贴吧签到失败'}
                        
        except Exception as e:
            logger.error(f"贴吧签到异常: {e}")
            return {'success': False, 'error': f'签到异常: {str(e)}'}
    
    async def _jd_checkin(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """京东签到"""
        try:
            cookies_str = account.get('cookies', '')
            if not cookies_str:
                return {'success': False, 'error': 'Cookies为空'}
            
            cookies = self._parse_cookies(cookies_str)
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://m.jd.com/',
                'Origin': 'https://m.jd.com'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 京东签到接口参数构建
                sign_params = {
                    'functionId': 'signBeanIndex',
                    'appid': 'ld',
                    'body': '{}',
                    'client': 'apple',
                    'clientVersion': '10.0.4'
                }
                
                async with session.post(
                    'https://api.m.jd.com/client.action',
                    data=sign_params,
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return {'success': False, 'error': f'签到请求失败: {resp.status}'}
                    
                    checkin_data = await resp.json()
                    
                    if checkin_data.get('code') == '0':
                        data = checkin_data.get('data', {})
                        return {
                            'success': True,
                            'points': data.get('dailyAward', 5),
                            'message': '签到成功',
                            'response_data': checkin_data
                        }
                    else:
                        return {
                            'success': False,
                            'error': checkin_data.get('msg', '签到失败'),
                            'response_data': checkin_data
                        }
                        
        except Exception as e:
            logger.error(f"京东签到异常: {e}")
            return {'success': False, 'error': f'签到异常: {str(e)}'}
    
    async def _v2ex_checkin(self, account: Dict[str, Any]) -> Dict[str, Any]:
        """V2EX签到"""
        try:
            cookies_str = account.get('cookies', '')
            if not cookies_str:
                return {'success': False, 'error': 'Cookies为空'}
            
            cookies = self._parse_cookies(cookies_str)
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://www.v2ex.com/',
                'Origin': 'https://www.v2ex.com'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                # 1. 获取签到页面获取once token
                async with session.get(
                    'https://www.v2ex.com/mission/daily',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return {'success': False, 'error': f'获取签到页面失败: {resp.status}'}
                    
                    html_content = await resp.text()
                    
                    # 检查是否已经签到
                    if '每日登录奖励已领取' in html_content:
                        return {
                            'success': True,
                            'points': 0,
                            'message': '今日已签到',
                            'already_signed': True
                        }
                    
                    # 解析once token
                    import re
                    once_match = re.search(r'once=(\d+)', html_content)
                    if not once_match:
                        return {'success': False, 'error': '无法获取once token'}
                    
                    once = once_match.group(1)
                
                # 2. 执行签到
                async with session.get(
                    f'https://www.v2ex.com/mission/daily/redeem?once={once}',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        return {
                            'success': True,
                            'points': 10,  # V2EX签到奖励铜币
                            'message': '签到成功'
                        }
                    else:
                        return {'success': False, 'error': f'签到失败: {resp.status}'}
                        
        except Exception as e:
            logger.error(f"V2EX签到异常: {e}")
            return {'success': False, 'error': f'签到异常: {str(e)}'}
    
    # ==================== 账号测试实现 ====================
    
    async def _test_bilibili_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str]:
        """测试B站账号"""
        try:
            cookies = self._parse_cookies(account_data.get('cookies', ''))
            
                        headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://www.bilibili.com/'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    'https://api.bilibili.com/x/web-interface/nav',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return False, f'请求失败: {resp.status}'
                    
                    data = await resp.json()
                    if data.get('code') != 0:
                        return False, f'API错误: {data.get("message")}'
                    
                    user_info = data.get('data', {})
                    if not user_info.get('isLogin'):
                        return False, 'Cookie已失效'
                    
                    return True, f'验证成功，用户: {user_info.get("uname", "Unknown")}'
                    
        except Exception as e:
            return False, f'测试异常: {str(e)}'
    
    async def _test_aliyundrive_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str]:
        """测试阿里云盘账号"""
        try:
            refresh_token = account_data.get('refresh_token', '')
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Content-Type': 'application/json'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    'https://auth.aliyundrive.com/v2/account/token',
                    json={'refresh_token': refresh_token, 'grant_type': 'refresh_token'},
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return False, f'请求失败: {resp.status}'
                    
                    data = await resp.json()
                    if data.get('access_token'):
                        user_name = data.get('user_name', 'Unknown')
                        return True, f'验证成功，用户: {user_name}'
                    else:
                        return False, 'refresh_token已失效'
                        
        except Exception as e:
            return False, f'测试异常: {str(e)}'
    
    async def _test_tieba_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str]:
        """测试贴吧账号"""
        try:
            cookies = self._parse_cookies(account_data.get('cookies', ''))
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://tieba.baidu.com/'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    'https://tieba.baidu.com/dc/common/tbs',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return False, f'请求失败: {resp.status}'
                    
                    data = await resp.json()
                    if data.get('is_login') == 1:
                        return True, '验证成功'
                    else:
                        return False, 'Cookie已失效'
                        
        except Exception as e:
            return False, f'测试异常: {str(e)}'
    
    async def _test_jd_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str]:
        """测试京东账号"""
        try:
            cookies = self._parse_cookies(account_data.get('cookies', ''))
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://m.jd.com/'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    'https://me-api.jd.com/user_new/info/GetJDUserInfoUnion',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return False, f'请求失败: {resp.status}'
                    
                    data = await resp.json()
                    if data.get('retcode') == '0':
                        user_info = data.get('data', {}).get('userInfo', {})
                        return True, f'验证成功，用户: {user_info.get("baseInfo", {}).get("nickname", "Unknown")}'
                    else:
                        return False, 'Cookie已失效'
                        
        except Exception as e:
            return False, f'测试异常: {str(e)}'
    
    async def _test_v2ex_account(self, account_data: Dict[str, Any]) -> Tuple[bool, str]:
        """测试V2EX账号"""
        try:
            cookies = self._parse_cookies(account_data.get('cookies', ''))
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Referer': 'https://www.v2ex.com/'
            }
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(
                    'https://www.v2ex.com/mission/daily',
                    cookies=cookies,
                    headers=headers
                ) as resp:
                    if resp.status != 200:
                        return False, f'请求失败: {resp.status}'
                    
                    html_content = await resp.text()
                    
                    if '你要查看的页面需要先登录' in html_content:
                        return False, 'Cookie已失效'
                    elif '每日登录奖励' in html_content:
                        return True, '验证成功'
                    else:
                        return False, '无法验证账号状态'
                        
        except Exception as e:
            return False, f'测试异常: {str(e)}'
    
    # ==================== 工具方法 ====================
    
    def _parse_cookies(self, cookies_str: str) -> Dict[str, str]:
        """解析Cookie字符串"""
        cookies = {}
        if not cookies_str:
            return cookies
        
        try:
            # 支持两种格式：
            # 1. name1=value1; name2=value2
            # 2. {"name1": "value1", "name2": "value2"}
            
            if cookies_str.strip().startswith('{'):
                # JSON格式
                import json
                cookies = json.loads(cookies_str)
            else:
                # 标准Cookie格式
                for item in cookies_str.split(';'):
                    item = item.strip()
                    if '=' in item:
                        name, value = item.split('=', 1)
                        cookies[name.strip()] = value.strip()
                        
        except Exception as e:
            logger.error(f"解析Cookie失败: {e}")
        
        return cookies
    
    def _format_cookies(self, cookies: Dict[str, str]) -> str:
        """格式化Cookie为字符串"""
        return '; '.join([f'{name}={value}' for name, value in cookies.items()])
    
    async def get_account_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """获取账号统计信息"""
        try:
            # 获取用户账号
            accounts = await self.database.get_user_accounts(user_id)
            
            if not accounts:
                return {
                    'total_accounts': 0,
                    'enabled_accounts': 0,
                    'account_types': {},
                    'checkin_stats': {}
                }
            
            # 统计账号类型
            account_types = {}
            enabled_count = 0
            
            for account in accounts:
                account_type = account.get('account_type', 'unknown')
                account_types[account_type] = account_types.get(account_type, 0) + 1
                
                if account.get('is_enabled'):
                    enabled_count += 1
            
            # 获取签到统计
            checkin_stats = await self.database.get_checkin_stats(user_id, days)
            
            return {
                'total_accounts': len(accounts),
                'enabled_accounts': enabled_count,
                'account_types': account_types,
                'checkin_stats': checkin_stats
            }
            
        except Exception as e:
            logger.error(f"获取账号统计失败: {e}")
            return {}
    
    async def refresh_account_tokens(self, account_id: int) -> bool:
        """刷新账号令牌"""
        try:
            account = await self.database.get_account(account_id)
            if not account:
                return False
            
            account_type = account.get('account_type')
            
            if account_type == 'aliyundrive':
                # 阿里云盘刷新token
                refresh_token = account.get('refresh_token')
                if not refresh_token:
                    return False
                
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Content-Type': 'application/json'
                }
                
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(
                        'https://auth.aliyundrive.com/v2/account/token',
                        json={'refresh_token': refresh_token, 'grant_type': 'refresh_token'},
                        headers=headers
                    ) as resp:
                        if resp.status != 200:
                            return False
                        
                        data = await resp.json()
                        new_access_token = data.get('access_token')
                        new_refresh_token = data.get('refresh_token')
                        
                        if new_access_token:
                            # 更新数据库中的token
                            update_data = {'access_token': new_access_token}
                            if new_refresh_token:
                                update_data['refresh_token'] = new_refresh_token
                            
                            return await self.database.update_account(account_id, update_data)
                
                return False
            else:
                # 其他类型暂不支持自动刷新
                return True
                
        except Exception as e:
            logger.error(f"刷新账号令牌失败: {e}")
            return False
    
    async def validate_all_accounts(self, user_id: int = None) -> Dict[str, Any]:
        """验证所有账号有效性"""
        try:
            # 获取需要验证的账号
            if user_id:
                accounts = await self.database.get_user_accounts(user_id)
            else:
                accounts = await self.database.get_all_accounts()
            
            results = {
                'total': len(accounts),
                'valid': 0,
                'invalid': 0,
                'details': []
            }
            
            for account in accounts:
                account_id = account['id']
                
                try:
                    is_valid, message = await self._test_account(account)
                    
                    results['details'].append({
                        'account_id': account_id,
                        'name': account.get('name'),
                        'type': account.get('account_type'),
                        'valid': is_valid,
                        'message': message
                    })
                    
                    if is_valid:
                        results['valid'] += 1
                        # 如果账号之前被禁用，重新启用
                        if not account.get('is_enabled'):
                            await self.database.update_account(account_id, {'is_enabled': True})
                    else:
                        results['invalid'] += 1
                        # 自动禁用无效账号
                        await self.database.update_account(account_id, {'is_enabled': False})
                    
                    # 添加小延迟
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"验证账号 {account_id} 异常: {e}")
                    results['invalid'] += 1
                    results['details'].append({
                        'account_id': account_id,
                        'name': account.get('name'),
                        'type': account.get('account_type'),
                        'valid': False,
                        'message': f'验证异常: {str(e)}'
                    })
            
            logger.info(f"账号验证完成: 总计 {results['total']}，有效 {results['valid']}，无效 {results['invalid']}")
            
            return results
            
        except Exception as e:
            logger.error(f"验证所有账号失败: {e}")
            return {'total': 0, 'valid': 0, 'invalid': 0, 'details': []}


# 全局账号管理器实例
account_manager = None

async def get_account_manager(database: Database = None, config: Config = None) -> AccountManager:
    """获取账号管理器实例"""
    global account_manager
    
    if account_manager is None:
        if not all([database, config]):
            raise ValueError("首次创建账号管理器需要提供所有依赖组件")
        account_manager = AccountManager(database, config)
    
    return account_manager

            


