"""
统一的基础类模块
"""

from .abstract import (
    BaseService,
    BaseAdapter,
    BaseAnalyst,
    BaseToolInterface,
    BaseProvider
)

from .exceptions import (
    BaseError,
    ValidationError,
    NotImplementedError,
    DataError,
    ConfigurationError,
    NetworkError,
    RateLimitError,
    AuthenticationError,
    AuthorizationError,
    TimeoutError,
    # 业务异常
    DataGatewayException,
    ProviderException,
    ToolRegistryException,
    ToolExecutionException,
    ValidationException
)

from .types import (
    Status,
    Priority,
    Result
)

__all__ = [
    # 基类
    "BaseService",
    "BaseAdapter", 
    "BaseAnalyst",
    "BaseToolInterface",
    "BaseProvider",
    
    # 异常
    "BaseError",
    "ValidationError",
    "NotImplementedError",
    "DataError",
    "ConfigurationError",
    
    # 类型
    "Status",
    "Priority",
    "Result"
]