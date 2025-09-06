"""
统一的异常定义
"""

from typing import Optional, Any, Dict


class BaseError(Exception):
    """基础异常类"""
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
        super().__init__(self.message)
        
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details
        }


class ValidationError(BaseError):
    """验证错误"""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.details["field"] = field


class NotImplementedError(BaseError):
    """未实现错误"""
    
    def __init__(self, feature: str, **kwargs):
        message = f"Feature not implemented: {feature}"
        super().__init__(message, **kwargs)


class DataError(BaseError):
    """数据错误"""
    
    def __init__(self, message: str, data_type: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if data_type:
            self.details["data_type"] = data_type


class ConfigurationError(BaseError):
    """配置错误"""
    
    def __init__(self, message: str, config_key: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        if config_key:
            self.details["config_key"] = config_key


class NetworkError(BaseError):
    """网络错误"""
    
    def __init__(self, message: str, url: Optional[str] = None, status_code: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        if url:
            self.details["url"] = url
        if status_code:
            self.details["status_code"] = status_code


class RateLimitError(BaseError):
    """速率限制错误"""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, **kwargs):
        super().__init__(message, **kwargs)
        if retry_after:
            self.details["retry_after"] = retry_after


class AuthenticationError(BaseError):
    """认证错误"""
    pass


class AuthorizationError(BaseError):
    """授权错误"""
    pass


class TimeoutError(BaseError):
    """超时错误"""
    
    def __init__(self, message: str, timeout: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        if timeout:
            self.details["timeout"] = timeout


# 业务相关异常
class DataGatewayException(BaseError):
    """数据网关异常"""
    pass


class ProviderException(BaseError):
    """数据提供者异常"""
    pass


class ToolRegistryException(BaseError):
    """工具注册表异常"""
    pass


class ToolExecutionException(BaseError):
    """工具执行异常"""
    pass


class ValidationException(BaseError):
    """验证异常（业务级）"""
    pass