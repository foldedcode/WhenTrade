"""
API重试和错误处理器

提供智能重试策略和详细的错误分类处理
"""
import time
import random
from typing import Callable, Dict, Any, Optional, List, Union, Type
from functools import wraps
import logging
from enum import Enum
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
import asyncio

logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """错误类型分类"""
    RATE_LIMIT = "rate_limit"        # 429错误
    AUTH_ERROR = "auth_error"        # 401/403错误
    NOT_FOUND = "not_found"          # 404错误
    SERVER_ERROR = "server_error"    # 5xx错误
    NETWORK_ERROR = "network_error"  # 网络连接错误
    TIMEOUT_ERROR = "timeout_error"  # 超时错误
    UNKNOWN_ERROR = "unknown_error"  # 未知错误


class RetryConfig:
    """重试配置"""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_errors: Optional[List[ErrorType]] = None
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        
        # 默认可重试的错误类型
        self.retryable_errors = retryable_errors or [
            ErrorType.RATE_LIMIT,
            ErrorType.SERVER_ERROR,
            ErrorType.NETWORK_ERROR,
            ErrorType.TIMEOUT_ERROR
        ]


class APIErrorHandler:
    """API错误处理器"""
    
    # 默认重试配置
    DEFAULT_CONFIG = RetryConfig()
    
    # 特定API的重试配置
    API_CONFIGS = {
        'coingecko': RetryConfig(
            max_retries=3,
            base_delay=2.0,      # CoinGecko建议的最小间隔
            max_delay=30.0,
            exponential_base=2.0
        ),
        'yfinance': RetryConfig(
            max_retries=2,       # Yahoo Finance比较稳定，少重试
            base_delay=1.0,
            max_delay=10.0
        ),
        'finnhub': RetryConfig(
            max_retries=3,
            base_delay=1.0,
            max_delay=30.0
        )
    }
    
    @staticmethod
    def classify_error(error: Exception, response: Optional[requests.Response] = None) -> ErrorType:
        """
        分类错误类型
        
        Args:
            error: 异常对象
            response: HTTP响应对象（如果有）
            
        Returns:
            错误类型枚举
        """
        # HTTP状态码错误
        if response is not None:
            status_code = response.status_code
            if status_code == 429:
                return ErrorType.RATE_LIMIT
            elif status_code in [401, 403]:
                return ErrorType.AUTH_ERROR
            elif status_code == 404:
                return ErrorType.NOT_FOUND
            elif 500 <= status_code < 600:
                return ErrorType.SERVER_ERROR
        
        # 异常类型错误
        if isinstance(error, Timeout):
            return ErrorType.TIMEOUT_ERROR
        elif isinstance(error, ConnectionError):
            return ErrorType.NETWORK_ERROR
        elif isinstance(error, RequestException):
            # 检查错误消息中的关键词
            error_msg = str(error).lower()
            if 'rate limit' in error_msg or 'too many requests' in error_msg:
                return ErrorType.RATE_LIMIT
            elif 'unauthorized' in error_msg or 'forbidden' in error_msg:
                return ErrorType.AUTH_ERROR
            elif 'timeout' in error_msg:
                return ErrorType.TIMEOUT_ERROR
            elif 'connection' in error_msg:
                return ErrorType.NETWORK_ERROR
            else:
                return ErrorType.UNKNOWN_ERROR
        
        return ErrorType.UNKNOWN_ERROR
    
    @staticmethod
    def get_retry_delay(
        attempt: int, 
        config: RetryConfig,
        error_type: ErrorType
    ) -> float:
        """
        计算重试延迟时间
        
        Args:
            attempt: 重试次数 (0-based)
            config: 重试配置
            error_type: 错误类型
            
        Returns:
            延迟时间（秒）
        """
        # 基础延迟
        base_delay = config.base_delay
        
        # 根据错误类型调整延迟
        if error_type == ErrorType.RATE_LIMIT:
            base_delay = max(base_delay, 5.0)  # 速率限制至少等待5秒
        elif error_type == ErrorType.SERVER_ERROR:
            base_delay = max(base_delay, 3.0)  # 服务器错误至少等待3秒
        
        # 指数退避
        delay = base_delay * (config.exponential_base ** attempt)
        
        # 限制最大延迟
        delay = min(delay, config.max_delay)
        
        # 添加随机抖动
        if config.jitter:
            jitter = random.uniform(0.5, 1.5)
            delay = delay * jitter
        
        return delay
    
    @staticmethod
    def format_error_message(
        error: Exception,
        error_type: ErrorType,
        attempt: int,
        max_retries: int,
        api_name: str = "unknown"
    ) -> str:
        """
        格式化错误消息
        
        Args:
            error: 异常对象
            error_type: 错误类型
            attempt: 当前重试次数
            max_retries: 最大重试次数
            api_name: API名称
            
        Returns:
            格式化的错误消息
        """
        error_icons = {
            ErrorType.RATE_LIMIT: "⏱️",
            ErrorType.AUTH_ERROR: "🔒",
            ErrorType.NOT_FOUND: "🔍",
            ErrorType.SERVER_ERROR: "🔥",
            ErrorType.NETWORK_ERROR: "🌐",
            ErrorType.TIMEOUT_ERROR: "⏰",
            ErrorType.UNKNOWN_ERROR: "❓"
        }
        
        icon = error_icons.get(error_type, "❌")
        
        if attempt < max_retries:
            return f"{icon} {api_name} API错误 ({error_type.value}): {str(error)} - 重试 {attempt + 1}/{max_retries}"
        else:
            return f"{icon} {api_name} API错误 ({error_type.value}): {str(error)} - 重试次数已用完"


def retry_on_error(
    api_name: str = "default",
    custom_config: Optional[RetryConfig] = None
):
    """
    错误重试装饰器
    
    Args:
        api_name: API名称，用于选择重试配置
        custom_config: 自定义重试配置
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            config = custom_config or APIErrorHandler.API_CONFIGS.get(api_name, APIErrorHandler.DEFAULT_CONFIG)
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                    
                    # 检查结果中的错误信息
                    if isinstance(result, dict) and 'error' in result:
                        error_msg = result['error']
                        
                        # 创建虚拟异常用于错误分类
                        virtual_error = Exception(error_msg)
                        error_type = APIErrorHandler.classify_error(virtual_error)
                        
                        # 检查是否应该重试
                        if attempt < config.max_retries and error_type in config.retryable_errors:
                            delay = APIErrorHandler.get_retry_delay(attempt, config, error_type)
                            
                            logger.warning(
                                APIErrorHandler.format_error_message(
                                    virtual_error, error_type, attempt, config.max_retries, api_name
                                ) + f" - 等待 {delay:.1f}s"
                            )
                            
                            await asyncio.sleep(delay)
                            continue
                    
                    return result
                    
                except Exception as e:
                    error_type = APIErrorHandler.classify_error(e)
                    
                    # 检查是否应该重试
                    if attempt < config.max_retries and error_type in config.retryable_errors:
                        delay = APIErrorHandler.get_retry_delay(attempt, config, error_type)
                        
                        logger.warning(
                            APIErrorHandler.format_error_message(
                                e, error_type, attempt, config.max_retries, api_name
                            ) + f" - 等待 {delay:.1f}s"
                        )
                        
                        await asyncio.sleep(delay)
                        continue
                    else:
                        # 不可重试的错误或重试次数用完
                        logger.error(
                            APIErrorHandler.format_error_message(
                                e, error_type, attempt, config.max_retries, api_name
                            )
                        )
                        
                        # 返回错误信息而不是抛出异常
                        return {
                            "error": str(e),
                            "error_type": error_type.value,
                            "api_name": api_name,
                            "attempts": attempt + 1,
                            "max_retries": config.max_retries
                        }
            
            # 理论上不会执行到这里，但为了安全性
            return {"error": "Maximum retries exceeded", "api_name": api_name}
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            config = custom_config or APIErrorHandler.API_CONFIGS.get(api_name, APIErrorHandler.DEFAULT_CONFIG)
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    # 检查结果中的错误信息
                    if isinstance(result, dict) and 'error' in result:
                        error_msg = result['error']
                        
                        # 创建虚拟异常用于错误分类
                        virtual_error = Exception(error_msg)
                        error_type = APIErrorHandler.classify_error(virtual_error)
                        
                        # 检查是否应该重试
                        if attempt < config.max_retries and error_type in config.retryable_errors:
                            delay = APIErrorHandler.get_retry_delay(attempt, config, error_type)
                            
                            logger.warning(
                                APIErrorHandler.format_error_message(
                                    virtual_error, error_type, attempt, config.max_retries, api_name
                                ) + f" - 等待 {delay:.1f}s"
                            )
                            
                            time.sleep(delay)
                            continue
                    
                    return result
                    
                except Exception as e:
                    error_type = APIErrorHandler.classify_error(e)
                    
                    # 检查是否应该重试
                    if attempt < config.max_retries and error_type in config.retryable_errors:
                        delay = APIErrorHandler.get_retry_delay(attempt, config, error_type)
                        
                        logger.warning(
                            APIErrorHandler.format_error_message(
                                e, error_type, attempt, config.max_retries, api_name
                            ) + f" - 等待 {delay:.1f}s"
                        )
                        
                        time.sleep(delay)
                        continue
                    else:
                        # 不可重试的错误或重试次数用完
                        logger.error(
                            APIErrorHandler.format_error_message(
                                e, error_type, attempt, config.max_retries, api_name
                            )
                        )
                        
                        # 返回错误信息而不是抛出异常
                        return {
                            "error": str(e),
                            "error_type": error_type.value,
                            "api_name": api_name,
                            "attempts": attempt + 1,
                            "max_retries": config.max_retries
                        }
            
            # 理论上不会执行到这里，但为了安全性
            return {"error": "Maximum retries exceeded", "api_name": api_name}
        
        # 根据函数类型返回对应的包装器
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator


def create_robust_tool_wrapper(tool_func: Callable, api_name: str = "default") -> Callable:
    """
    创建具有重试和限流功能的健壮工具包装器
    
    Args:
        tool_func: 原始工具函数
        api_name: API名称
        
    Returns:
        包装后的工具函数
    """
    from .rate_limiter import rate_limit
    
    # 先应用重试装饰器，再应用限流装饰器
    @rate_limit(api_name=api_name, use_cache=True)
    @retry_on_error(api_name=api_name)
    @wraps(tool_func)
    def wrapper(*args, **kwargs):
        return tool_func(*args, **kwargs)
    
    return wrapper