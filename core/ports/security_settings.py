"""
安全设置接口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum


class SessionStatus(str, Enum):
    """会话状态枚举"""
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


@dataclass
class UserSession:
    """用户会话数据模型"""
    id: int
    user_id: int
    session_token: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    created_at: datetime
    last_activity: datetime
    is_active: bool
    status: SessionStatus


@dataclass
class LoginHistory:
    """登录历史记录"""
    id: int
    user_id: int
    ip_address: Optional[str]
    user_agent: Optional[str]
    login_time: datetime
    success: bool
    failure_reason: Optional[str]


@dataclass
class ApiKey:
    """API密钥数据模型"""
    id: int
    user_id: int
    name: str
    key_prefix: str  # 前缀，用于显示
    permissions: List[str]
    last_used: Optional[datetime]
    created_at: datetime
    expires_at: Optional[datetime]
    is_active: bool


@dataclass
class SecuritySettings:
    """安全设置汇总"""
    two_factor_enabled: bool
    last_password_change: Optional[datetime]
    active_sessions_count: int
    api_keys_count: int
    suspicious_activity_detected: bool


@dataclass
class PasswordChangeRequest:
    """密码修改请求"""
    current_password: str
    new_password: str


@dataclass
class TwoFactorSetupResult:
    """双因素认证设置结果"""
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class SecuritySettingsPort(ABC):
    """安全设置接口"""
    
    @abstractmethod
    async def get_security_settings(self, user_id: int) -> SecuritySettings:
        """获取安全设置汇总"""
        pass
    
    @abstractmethod
    async def change_password(
        self,
        user_id: int,
        request: PasswordChangeRequest
    ) -> bool:
        """修改密码"""
        pass
    
    @abstractmethod
    async def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """获取活跃会话"""
        pass
    
    @abstractmethod
    async def revoke_session(self, user_id: int, session_id: int) -> bool:
        """撤销会话"""
        pass
    
    @abstractmethod
    async def revoke_all_sessions(self, user_id: int) -> int:
        """撤销所有会话，返回撤销数量"""
        pass
    
    @abstractmethod
    async def get_login_history(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[LoginHistory]:
        """获取登录历史"""
        pass
    
    @abstractmethod
    async def setup_two_factor(self, user_id: int) -> TwoFactorSetupResult:
        """设置双因素认证"""
        pass
    
    @abstractmethod
    async def verify_two_factor(
        self,
        user_id: int,
        code: str
    ) -> bool:
        """验证双因素认证码"""
        pass
    
    @abstractmethod
    async def disable_two_factor(
        self,
        user_id: int,
        password: str
    ) -> bool:
        """禁用双因素认证"""
        pass
    
    @abstractmethod
    async def get_api_keys(self, user_id: int) -> List[ApiKey]:
        """获取API密钥列表"""
        pass
    
    @abstractmethod
    async def create_api_key(
        self,
        user_id: int,
        name: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[ApiKey, str]:
        """创建API密钥，返回密钥信息和完整密钥"""
        pass
    
    @abstractmethod
    async def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        """撤销API密钥"""
        pass