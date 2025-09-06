"""
统一API执行器 - Linus式设计

单一入口点处理所有API调用，内置限流、缓存、重试机制
消除装饰器复杂性，简化数据流
"""
import time
import random
import asyncio
from functools import wraps
from typing import Callable, Dict, Any, Optional, List
from collections import defaultdict
import logging
import hashlib
import json

logger = logging.getLogger(__name__)

# 全局APIExecutor实例 - 单例模式
_api_executor_instance = None

def get_api_executor(websocket=None) -> 'APIExecutor':
    """获取全局APIExecutor实例"""
    global _api_executor_instance
    if _api_executor_instance is None or (websocket and not _api_executor_instance.websocket):
        _api_executor_instance = APIExecutor(websocket)
    elif websocket and _api_executor_instance.websocket != websocket:
        # 如果websocket不同，更新现有实例的websocket
        _api_executor_instance.websocket = websocket
    return _api_executor_instance


class APIExecutor:
    """统一API执行器 - 所有API调用的单一入口点"""
    
    def __init__(self, websocket=None):
        # 速率限制器配置
        self.rate_limits = {
            'coingecko': {'max_calls': 10, 'window': 60, 'calls': []},
            'yfinance': {'max_calls': 5, 'window': 60, 'calls': []},  # 进一步降低到5次/分钟，避免429错误
            'finnhub': {'max_calls': 60, 'window': 60, 'calls': []},
            'reddit': {'max_calls': 60, 'window': 60, 'calls': []},
            'default': {'max_calls': 30, 'window': 60, 'calls': []}
        }
        
        # 缓存存储 {key: (result, timestamp)}
        self.cache: Dict[str, tuple] = {}
        self.cache_ttl = 300  # 5分钟
        
        # 重试配置 - 优化延迟时间
        self.retry_configs = {
            'coingecko': {'max_retries': 2, 'base_delay': 3.0, 'max_delay': 10.0, 'min_interval': 2.0},  # 🔧 CoinGecko速率限制优化
            'yfinance': {'max_retries': 3, 'base_delay': 5.0, 'max_delay': 15.0},  # 429错误特殊处理
            'finnhub': {'max_retries': 3, 'base_delay': 1.0, 'max_delay': 10.0},
            'default': {'max_retries': 3, 'base_delay': 1.0, 'max_delay': 10.0}
        }
        
        # 停止事件支持 - Linus式中断机制
        self.stop_event = None
        
        # WebSocket通知支持 - 实时状态推送
        self.websocket = websocket
        
        logger.info("🔧 APIExecutor initialized - 统一API执行器已启动")    
    def set_stop_event(self, stop_event):
        """设置停止事件 - 用于中断长时间运行的API调用"""
        self.stop_event = stop_event
        logger.debug("🛑 [APIExecutor] 设置停止事件")
    
    def _is_stopped(self) -> bool:
        """检查是否收到停止信号"""
        return self.stop_event is not None and self.stop_event.is_set()

    
    async def _send_tool_status(self, tool_name: str, status: str, **kwargs):
        """发送工具状态通知到前端"""
        if not self.websocket:
            return
            
        try:
            message = {
                "type": "tool.status",
                "data": {
                    "tool_name": tool_name,
                    "status": status,
                    **kwargs
                }
            }
            await self.websocket.send_json(message)
            logger.debug(f"📤 工具状态通知: {tool_name} - {status}")
        except Exception as e:
            logger.error(f"❌ 发送工具状态通知失败: {e}")
    
    def _send_tool_status_sync(self, tool_name: str, status: str, **kwargs):
        """同步版本的工具状态通知 - 用于同步上下文"""
        if not self.websocket:
            return
            
        import asyncio
        try:
            # 在事件循环中运行异步方法
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果循环正在运行，创建任务
                asyncio.create_task(self._send_tool_status(tool_name, status, **kwargs))
            else:
                # 如果循环未运行，直接运行
                loop.run_until_complete(self._send_tool_status(tool_name, status, **kwargs))
        except Exception as e:
            logger.error(f"❌ 同步发送工具状态通知失败: {e}")
    
    def _interruptible_sleep(self, duration: float, tool_name: str) -> bool:
        """可中断的睡眠 - 在等待期间检查停止信号
        
        Args:
            duration: 睡眠时间（秒）
            tool_name: 工具名称（用于日志）
        
        Returns:
            True: 收到停止信号，已中断
            False: 正常完成等待
        """
        # 分割长等待时间，每0.5秒检查一次停止信号
        check_interval = 0.5
        elapsed = 0.0
        
        while elapsed < duration:
            if self._is_stopped():
                logger.info(f"🛑 {tool_name} 等待期间收到停止信号")
                return True
            
            # 睡眠最多check_interval秒
            sleep_time = min(check_interval, duration - elapsed)
            time.sleep(sleep_time)
            elapsed += sleep_time
        
        return False
    
    def _make_cache_key(self, func: Callable, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        func_name = getattr(func, '__name__', str(func))
        
        # 对价格数据请求使用智能缓存键
        if ('get_historical_prices' in func_name or 
            'get_crypto_price' in func_name or 
            'coingecko_price_adapter' in func_name):
            return self._make_price_cache_key(kwargs)
        
        # 其他请求使用原有逻辑
        key_data = {
            'function': func_name,
            'args': args,
            'kwargs': {k: v for k, v in sorted(kwargs.items())}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def _make_price_cache_key(self, kwargs: dict) -> str:
        """为价格数据生成智能缓存键，支持数据复用"""
        symbol = kwargs.get('symbol', '').lower()
        
        # 使用日期而非精确时间戳，提高缓存命中率
        from datetime import datetime
        date_key = datetime.now().strftime('%Y%m%d')
        
        # 对于历史数据，考虑日期范围
        if 'start_date' in kwargs and 'end_date' in kwargs:
            start_date = kwargs['start_date']
            end_date = kwargs['end_date']
            cache_key = f"price_range_{symbol}_{start_date}_{end_date}"
        elif 'days' in kwargs:
            days = kwargs['days']
            cache_key = f"price_days_{symbol}_{days}_{date_key}"
        else:
            cache_key = f"price_current_{symbol}_{date_key}"
        
        return cache_key
    
    def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取结果"""
        if cache_key in self.cache:
            result, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                logger.debug("📋 缓存命中")
                return result
            else:
                # 清理过期缓存
                del self.cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, result: Any):
        """设置缓存"""
        self.cache[cache_key] = (result, time.time())
        logger.debug("💾 缓存已保存")
    
    def _check_rate_limit(self, api_name: str) -> bool:
        """检查速率限制"""
        config = self.rate_limits.get(api_name, self.rate_limits['default'])
        now = time.time()
        
        # 清理过期调用记录
        config['calls'] = [call_time for call_time in config['calls'] 
                          if now - call_time < config['window']]
        
        # 检查是否超出限制
        if len(config['calls']) >= config['max_calls']:
            return False
        
        # 记录本次调用
        config['calls'].append(now)
        return True
    
    def _wait_for_rate_limit(self, api_name: str):
        """等待速率限制重置"""
        config = self.rate_limits.get(api_name, self.rate_limits['default'])
        if config['calls']:
            oldest_call = min(config['calls'])
            wait_time = config['window'] - (time.time() - oldest_call)
            if wait_time > 0:
                logger.warning(f"⏱️ 速率限制：等待 {wait_time:.1f} 秒")
                time.sleep(wait_time + 0.1)  # 额外0.1秒缓冲
    
    def _classify_error(self, error: Exception, result: Dict = None) -> str:
        """分类错误类型"""
        error_msg = str(error).lower()
        
        # 检查结果中的错误信息
        if result and isinstance(result, dict) and 'error' in result:
            error_msg = str(result['error']).lower()
        
        # 🔧 增强：CoinGecko特定错误处理
        if 'rate limit' in error_msg or 'too many requests' in error_msg or '429' in error_msg:
            logger.warning(f"📊 [API限制] 检测到速率限制错误: {error_msg[:100]}")
            return 'rate_limit'
        elif '10005' in error_msg:  # CoinGecko Pro API限制
            logger.warning(f"🔒 [CoinGecko] Pro API端点访问限制: {error_msg[:100]}")
            return 'auth_error'
        elif '10002' in error_msg or '10010' in error_msg or '10011' in error_msg:  # CoinGecko API Key问题
            logger.error(f"🔑 [CoinGecko] API密钥问题: {error_msg[:100]}")
            return 'auth_error'
        elif 'unauthorized' in error_msg or '401' in error_msg or '403' in error_msg:
            return 'auth_error'
        elif 'timeout' in error_msg:
            return 'timeout'
        elif 'ssl' in error_msg or 'eof' in error_msg or 'unexpected_eof_while_reading' in error_msg:
            return 'network'  # SSL错误按网络错误处理，支持重试
        elif 'connection' in error_msg or 'network' in error_msg:
            return 'network'
        elif '5' in error_msg[:3]:  # 5xx错误
            return 'server_error'
        else:
            return 'unknown'
    
    def _should_retry(self, error_type: str) -> bool:
        """判断是否应该重试"""
        retryable_errors = {'rate_limit', 'server_error', 'network', 'timeout'}
        return error_type in retryable_errors
    
    def _calculate_retry_delay(self, attempt: int, api_name: str, error_type: str) -> float:
        """计算重试延迟"""
        config = self.retry_configs.get(api_name, self.retry_configs['default'])
        base_delay = config['base_delay']
        
        # 根据错误类型调整基础延迟
        if error_type == 'rate_limit':
            base_delay = max(base_delay, 5.0)  # 速率限制至少等待5秒
        elif error_type == 'server_error':
            base_delay = max(base_delay, 3.0)  # 服务器错误至少等待3秒
        
        # 指数退避
        delay = base_delay * (2 ** attempt)
        delay = min(delay, config['max_delay'])
        
        # 添加随机抖动
        jitter = random.uniform(0.5, 1.5)
        delay = delay * jitter
        
        return delay

    
    def _enforce_min_interval(self, api_name: str):
        """确保API调用最小间隔，防止连续请求"""
        # 🔧 增强：支持retry_configs中的min_interval配置
        config = self.retry_configs.get(api_name, self.retry_configs['default'])
        config_interval = config.get('min_interval', 0)
        
        # 传统间隔配置作为后备
        min_intervals = {
            'yfinance': 5.0,  # YFinance至少5秒间隔，更保守的限制
            'coingecko': 2.0,  # 🔧 CoinGecko增加到2秒间隔，应对速率限制
            'finnhub': 1.0,   # Finnhub至少1秒间隔
            'reddit': 1.0,    # Reddit至少1秒间隔
            'default': 0.5    # 默认0.5秒间隔
        }
        
        # 使用配置中的min_interval或传统配置
        interval = max(config_interval, min_intervals.get(api_name, min_intervals['default']))
        if interval > 0:
            logger.debug(f"⏱️ API间隔控制：{api_name} 等待 {interval}s")
            time.sleep(interval)
    
    def call(
        self, 
        tool_name: str,
        func: Callable, 
        api_name: str = 'default',
        use_cache: bool = True,
        **kwargs
    ) -> Any:
        """
        执行API调用 - 统一入口点
        
        Args:
            tool_name: 工具名称（用于日志）
            func: 要调用的函数
            api_name: API名称（用于速率限制）
            use_cache: 是否使用缓存
            **kwargs: 传递给函数的参数
        
        Returns:
            函数执行结果
        """
        start_time = time.time()
        
        # 1. 缓存检查
        cache_key = None
        if use_cache:
            cache_key = self._make_cache_key(func, (), kwargs)
            cached_result = self._get_from_cache(cache_key)
            if cached_result is not None:
                logger.info(f"📋 {tool_name} 缓存命中")
                self._send_tool_status_sync(tool_name, "cache_hit", duration=0.0)
                return cached_result
        
        # 2. 重试循环
        config = self.retry_configs.get(api_name, self.retry_configs['default'])
        for attempt in range(config['max_retries'] + 1):
            # 检查停止信号 - Linus式早期退出
            if self._is_stopped():
                logger.info(f"🛑 {tool_name} 收到停止信号，中断执行")
                self._send_tool_status_sync(tool_name, "cancelled")
                return {"error": "Operation cancelled by user", "cancelled": True}
            
            try:
                # 3. 速率限制检查
                if not self._check_rate_limit(api_name):
                    self._wait_for_rate_limit(api_name)
                    continue
                
                # 3.5. 预防性延迟控制
                self._enforce_min_interval(api_name)
                
                # 4. 执行API调用
                logger.info(f"🎯 执行 {tool_name} (尝试 {attempt + 1}/{config['max_retries'] + 1})")
                if attempt > 0:
                    # 发送重试通知
                    self._send_tool_status_sync(
                        tool_name, 
                        "retry",
                        attempt=attempt + 1,
                        max_attempts=config['max_retries'] + 1
                    )
                
                result = func(**kwargs)
                
                # 5. 检查结果中的错误
                if isinstance(result, dict) and 'error' in result:
                    error_type = self._classify_error(None, result)
                    
                    if attempt < config['max_retries'] and self._should_retry(error_type):
                        delay = self._calculate_retry_delay(attempt, api_name, error_type)
                        logger.warning(f"⚠️ {tool_name} 失败({error_type}): {result['error'][:100]} - 重试 {delay:.1f}s后")
                        
                        # 发送重试通知，包含错误信息和延迟
                        self._send_tool_status_sync(
                            tool_name,
                            "retry_pending", 
                            attempt=attempt + 1,
                            max_attempts=config['max_retries'] + 1,
                            error=result['error'][:100],
                            delay=delay
                        )
                        
                        # 在等待期间检查停止信号
                        if self._interruptible_sleep(delay, tool_name):
                            self._send_tool_status_sync(tool_name, "cancelled")
                            return {"error": "Operation cancelled during retry wait", "cancelled": True}
                        continue
                    else:
                        logger.error(f"❌ {tool_name} 最终失败: {result['error'][:100]}")
                        self._send_tool_status_sync(
                            tool_name,
                            "failed",
                            error=result['error'][:100],
                            attempts=attempt + 1
                        )
                        return result
                
                # 6. 成功 - 缓存结果
                duration = time.time() - start_time
                logger.info(f"✅ {tool_name} 成功 - {duration:.2f}s")
                
                # 发送成功通知
                self._send_tool_status_sync(
                    tool_name,
                    "success",
                    duration=duration,
                    attempts=attempt + 1
                )
                
                if use_cache and cache_key:
                    self._set_cache(cache_key, result)
                
                return result
                
            except Exception as e:
                error_type = self._classify_error(e)
                
                if attempt < config['max_retries'] and self._should_retry(error_type):
                    delay = self._calculate_retry_delay(attempt, api_name, error_type)
                    logger.warning(f"⚠️ {tool_name} 异常({error_type}): {str(e)[:100]} - 重试 {delay:.1f}s后")
                    
                    # 发送重试通知
                    self._send_tool_status_sync(
                        tool_name,
                        "retry_pending",
                        attempt=attempt + 1,
                        max_attempts=config['max_retries'] + 1,
                        error=str(e)[:100],
                        delay=delay
                    )
                    
                    # 在等待期间检查停止信号
                    if self._interruptible_sleep(delay, tool_name):
                        self._send_tool_status_sync(tool_name, "cancelled")
                        return {"error": "Operation cancelled during retry wait", "cancelled": True}
                    continue
                else:
                    duration = time.time() - start_time
                    logger.error(f"❌ {tool_name} 异常失败: {str(e)[:100]} - {duration:.2f}s")
                    
                    # 发送失败通知
                    self._send_tool_status_sync(
                        tool_name,
                        "failed",
                        error=str(e)[:100],
                        attempts=attempt + 1,
                        duration=duration
                    )
                    
                    return {
                        "error": str(e),
                        "error_type": error_type,
                        "tool_name": tool_name,
                        "api_name": api_name,
                        "attempts": attempt + 1
                    }
        
        # 理论上不会执行到这里
        self._send_tool_status_sync(tool_name, "failed", error="Maximum retries exceeded")
        return {"error": "Maximum retries exceeded", "tool_name": tool_name}

    
    def call_with_fallback(
        self,
        tool_name: str,
        primary_func: Callable,
        primary_api: str = 'coingecko',
        fallback_func: Callable = None,
        fallback_api: str = 'yfinance',
        use_cache: bool = True,
        **kwargs
    ) -> Any:
        """
        带故障转移的API调用 - Linus式故障转移设计
        
        Args:
            tool_name: 工具名称
            primary_func: 主数据源函数
            primary_api: 主数据源API名称
            fallback_func: 备用数据源函数
            fallback_api: 备用数据源API名称
            use_cache: 是否使用缓存
            **kwargs: 传递给函数的参数
            
        Returns:
            函数执行结果
            
        Raises:
            Exception: 当所有数据源都失败时
        """
        logger.info(f"🔄 [故障转移] {tool_name}: {primary_api}(主) → {fallback_api if fallback_func else '无'}(备)")
        
        # 尝试主数据源
        try:
            logger.info(f"📊 [故障转移] 尝试主数据源: {primary_api}")
            result = self.call(tool_name + f"({primary_api})", primary_func, primary_api, use_cache, **kwargs)
            
            # 检查是否有错误
            if isinstance(result, dict) and 'error' in result:
                error_msg = str(result['error'])
                logger.warning(f"⚠️ [故障转移] 主数据源失败: {error_msg[:100]}")
                
                # 如果有备用数据源，尝试备用
                if fallback_func:
                    logger.info(f"🔄 [故障转移] 切换到备用数据源: {fallback_api}")
                    fallback_result = self.call(tool_name + f"({fallback_api})", fallback_func, fallback_api, use_cache, **kwargs)
                    
                    # 检查备用数据源结果
                    if isinstance(fallback_result, dict) and 'error' in fallback_result:
                        logger.error(f"❌ [故障转移] 备用数据源也失败: {str(fallback_result['error'])[:100]}")
                        # 返回错误字典而非抛异常 - Linus式：消除特殊情况
                        return {
                            "error": "所有数据源都失败",
                            "primary_api": primary_api,
                            "primary_error": error_msg[:100],
                            "fallback_api": fallback_api, 
                            "fallback_error": str(fallback_result['error'])[:100],
                            "tool_name": tool_name
                        }
                    else:
                        logger.info(f"✅ [故障转移] 备用数据源成功: {fallback_api}")
                        return fallback_result
                else:
                    # 没有备用数据源，返回错误字典而非抛异常 - Linus式：消除特殊情况
                    logger.error(f"❌ [故障转移] 无备用数据源，分析停止")
                    return {
                        "error": f"数据获取失败且无备用数据源",
                        "primary_api": primary_api,
                        "primary_error": error_msg[:150],
                        "fallback_api": "none",
                        "fallback_error": "无备用数据源",
                        "tool_name": tool_name
                    }
            else:
                logger.info(f"✅ [故障转移] 主数据源成功: {primary_api}")
                return result
                
        except Exception as e:
            # 主数据源异常，尝试备用
            if fallback_func:
                logger.warning(f"⚠️ [故障转移] 主数据源异常: {str(e)[:100]}")
                logger.info(f"🔄 [故障转移] 切换到备用数据源: {fallback_api}")
                
                try:
                    fallback_result = self.call(tool_name + f"({fallback_api})", fallback_func, fallback_api, use_cache, **kwargs)
                    
                    if isinstance(fallback_result, dict) and 'error' in fallback_result:
                        logger.error(f"❌ [故障转移] 备用数据源失败: {str(fallback_result['error'])[:100]}")
                        # 返回错误字典而非抛异常 - Linus式：消除特殊情况
                        return {
                            "error": "所有数据源都失败",
                            "primary_api": primary_api,
                            "primary_error": f"异常: {str(e)[:100]}",
                            "fallback_api": fallback_api,
                            "fallback_error": str(fallback_result['error'])[:100],
                            "tool_name": tool_name
                        }
                    else:
                        logger.info(f"✅ [故障转移] 备用数据源成功: {fallback_api}")
                        return fallback_result
                        
                except Exception as fallback_e:
                    logger.error(f"❌ [故障转移] 备用数据源异常: {str(fallback_e)[:100]}")
                    # 返回错误字典而非抛异常 - Linus式：消除特殊情况
                    return {
                        "error": "所有数据源都失败",
                        "primary_api": primary_api,
                        "primary_error": f"异常: {str(e)[:100]}",
                        "fallback_api": fallback_api,
                        "fallback_error": f"异常: {str(fallback_e)[:100]}",
                        "tool_name": tool_name
                    }
            else:
                # 没有备用数据源，返回错误字典而非抛异常 - Linus式：消除特殊情况
                logger.error(f"❌ [故障转移] 无备用数据源，分析停止")
                return {
                    "error": f"主数据源失败且无备用数据源",
                    "primary_api": primary_api,
                    "primary_error": f"异常: {str(e)[:150]}",
                    "fallback_api": "none",
                    "fallback_error": "无备用数据源",
                    "tool_name": tool_name
                }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        now = time.time()
        stats = {}
        
        for api_name, config in self.rate_limits.items():
            # 清理过期记录
            config['calls'] = [call_time for call_time in config['calls'] 
                             if now - call_time < config['window']]
            
            stats[api_name] = {
                'max_calls': config['max_calls'],
                'window': config['window'],
                'current_calls': len(config['calls']),
                'remaining_calls': max(0, config['max_calls'] - len(config['calls']))
            }
        
        stats['cache'] = {
            'total_entries': len(self.cache),
            'ttl': self.cache_ttl
        }
        
        return stats
    
    def clear_cache(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("🗑️ API缓存已清空")


# 全局便捷接口函数使用单例实例


def api_call(tool_name: str, func: Callable, api_name: str = 'default', use_cache: bool = True, stop_event=None, websocket=None, **kwargs) -> Any:
    """
    便捷的API调用接口
    
    Args:
        tool_name: 工具名称
        func: 要调用的函数
        api_name: API名称
        use_cache: 是否使用缓存
        stop_event: 停止事件，用于中断执行
        websocket: WebSocket连接，用于状态通知
        **kwargs: 传递给函数的参数
    
    Returns:
        函数执行结果
    """
    executor = get_api_executor(websocket)
    if stop_event:
        executor.set_stop_event(stop_event)
    return executor.call(tool_name, func, api_name, use_cache, **kwargs)


def api_call_with_fallback(
    tool_name: str, 
    primary_func: Callable, 
    primary_api: str = 'coingecko',
    fallback_func: Callable = None,
    fallback_api: str = 'yfinance',
    use_cache: bool = True,
    stop_event=None,
    websocket=None,
    **kwargs
) -> Any:
    """
    带故障转移的便捷API调用接口
    
    Args:
        tool_name: 工具名称
        primary_func: 主数据源函数
        primary_api: 主数据源API名称
        fallback_func: 备用数据源函数
        fallback_api: 备用数据源API名称
        use_cache: 是否使用缓存
        stop_event: 停止事件，用于中断执行
        websocket: WebSocket连接，用于状态通知
        **kwargs: 传递给函数的参数
    
    Returns:
        函数执行结果
        
    Raises:
        Exception: 当所有数据源都失败时
    """
    executor = get_api_executor(websocket)
    if stop_event:
        executor.set_stop_event(stop_event)
    return executor.call_with_fallback(
        tool_name, primary_func, primary_api, fallback_func, fallback_api, use_cache, **kwargs
    )
