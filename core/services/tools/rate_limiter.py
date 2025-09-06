"""
API请求限流器

为外部API调用提供速率限制和缓存功能，防止触发API服务商的限制。
"""
import asyncio
import time
from functools import wraps
from typing import Dict, Any, Optional, Callable, Tuple
from collections import defaultdict
import logging
import hashlib
import json

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, max_calls: int, time_window: int = 60):
        """
        初始化速率限制器
        
        Args:
            max_calls: 时间窗口内最大调用次数
            time_window: 时间窗口（秒）
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = defaultdict(list)
        self.locks = defaultdict(asyncio.Lock)
    
    async def acquire(self, key: str = "default") -> bool:
        """
        获取调用许可
        
        Args:
            key: 限流键（用于区分不同的API）
            
        Returns:
            是否获得许可
        """
        async with self.locks[key]:
            now = time.time()
            # 清理过期记录
            self.calls[key] = [call_time for call_time in self.calls[key] 
                             if now - call_time < self.time_window]
            
            # 检查是否超出限制
            if len(self.calls[key]) >= self.max_calls:
                oldest_call = min(self.calls[key])
                wait_time = self.time_window - (now - oldest_call)
                if wait_time > 0:
                    logger.warning(f"⏱️ 速率限制：{key} 需要等待 {wait_time:.1f} 秒")
                    await asyncio.sleep(wait_time + 0.1)  # 额外0.1秒缓冲
            
            # 记录本次调用
            self.calls[key].append(time.time())
            return True


class APICache:
    """API结果缓存"""
    
    def __init__(self, ttl: int = 300):
        """
        初始化缓存
        
        Args:
            ttl: 缓存生存时间（秒）
        """
        self.ttl = ttl
        self.cache: Dict[str, Tuple[Any, float]] = {}
    
    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """生成缓存键"""
        # 将参数序列化为稳定的字符串
        key_data = {
            'function': func_name,
            'args': args,
            'kwargs': {k: v for k, v in sorted(kwargs.items())}
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, func_name: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """获取缓存结果"""
        key = self._make_key(func_name, args, kwargs)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                logger.debug(f"📋 缓存命中: {func_name}")
                return result
            else:
                # 清理过期缓存
                del self.cache[key]
        return None
    
    def set(self, func_name: str, args: tuple, kwargs: dict, result: Any):
        """设置缓存结果"""
        key = self._make_key(func_name, args, kwargs)
        self.cache[key] = (result, time.time())
        logger.debug(f"💾 缓存保存: {func_name}")
    
    def clear(self):
        """清理所有缓存"""
        self.cache.clear()
        logger.info("🗑️ 已清理所有API缓存")


# 全局实例
_rate_limiters = {
    'coingecko': RateLimiter(max_calls=10, time_window=60),  # CoinGecko 免费版: 10次/分钟
    'yfinance': RateLimiter(max_calls=48, time_window=60),   # YFinance: 约48次/分钟
    'finnhub': RateLimiter(max_calls=60, time_window=60),    # Finnhub: 60次/分钟
    'reddit': RateLimiter(max_calls=60, time_window=60),     # Reddit API: 60次/分钟
    'default': RateLimiter(max_calls=30, time_window=60)     # 默认限制
}

_api_cache = APICache(ttl=300)  # 5分钟缓存


def rate_limit(api_name: str = 'default', use_cache: bool = True):
    """
    API速率限制装饰器
    
    Args:
        api_name: API名称，用于选择对应的限流器
        use_cache: 是否启用缓存
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # 检查缓存
            if use_cache:
                cached_result = _api_cache.get(func.__name__, args, kwargs)
                if cached_result is not None:
                    return cached_result
            
            # 获取速率限制许可
            limiter = _rate_limiters.get(api_name, _rate_limiters['default'])
            await limiter.acquire(api_name)
            
            # 执行函数
            try:
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # 缓存成功结果
                if use_cache and isinstance(result, dict) and 'error' not in result:
                    _api_cache.set(func.__name__, args, kwargs, result)
                
                return result
                
            except Exception as e:
                logger.error(f"❌ API调用失败 {func.__name__}: {e}")
                return {"error": str(e), "api_name": api_name}
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # 对于同步函数，使用简化的限流逻辑
            if use_cache:
                cached_result = _api_cache.get(func.__name__, args, kwargs)
                if cached_result is not None:
                    return cached_result
            
            # 同步版本的简单限流
            limiter = _rate_limiters.get(api_name, _rate_limiters['default'])
            now = time.time()
            
            # 简化的同步限流检查
            key = api_name
            limiter.calls[key] = [call_time for call_time in limiter.calls[key] 
                                if now - call_time < limiter.time_window]
            
            if len(limiter.calls[key]) >= limiter.max_calls:
                oldest_call = min(limiter.calls[key]) if limiter.calls[key] else now
                wait_time = limiter.time_window - (now - oldest_call)
                if wait_time > 0:
                    logger.warning(f"⏱️ 同步速率限制：{key} 等待 {wait_time:.1f} 秒")
                    time.sleep(wait_time + 0.1)
            
            limiter.calls[key].append(now)
            
            # 执行函数
            try:
                result = func(*args, **kwargs)
                
                # 缓存成功结果
                if use_cache and isinstance(result, dict) and 'error' not in result:
                    _api_cache.set(func.__name__, args, kwargs, result)
                
                return result
                
            except Exception as e:
                logger.error(f"❌ API调用失败 {func.__name__}: {e}")
                return {"error": str(e), "api_name": api_name}
        
        # 根据函数类型返回对应的包装器
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def clear_cache():
    """清理所有API缓存"""
    _api_cache.clear()


def get_rate_limit_stats() -> Dict[str, Dict[str, Any]]:
    """获取速率限制统计信息"""
    stats = {}
    now = time.time()
    
    for api_name, limiter in _rate_limiters.items():
        # 清理过期记录
        for key in limiter.calls:
            limiter.calls[key] = [call_time for call_time in limiter.calls[key] 
                                if now - call_time < limiter.time_window]
        
        # 统计信息
        total_calls = sum(len(calls) for calls in limiter.calls.values())
        stats[api_name] = {
            'max_calls': limiter.max_calls,
            'time_window': limiter.time_window,
            'current_calls': total_calls,
            'remaining_calls': max(0, limiter.max_calls - total_calls),
            'keys': list(limiter.calls.keys())
        }
    
    # 缓存统计
    stats['cache'] = {
        'total_entries': len(_api_cache.cache),
        'ttl': _api_cache.ttl
    }
    
    return stats