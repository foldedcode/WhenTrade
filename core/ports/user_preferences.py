"""
用户偏好设置接口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class NotificationType(str, Enum):
    """通知类型枚举"""
    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"


class NotificationCategory(str, Enum):
    """通知类别枚举"""
    SECURITY = "security"
    ACCOUNT = "account"
    TRADING = "trading"
    COST_ALERT = "cost_alert"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"


@dataclass
class NotificationPreference:
    """通知偏好设置"""
    category: NotificationCategory
    email_enabled: bool
    in_app_enabled: bool
    push_enabled: bool


@dataclass
class UserPreferences:
    """用户偏好设置数据模型"""
    user_id: int
    language_preference: str
    timezone: str
    theme: str  # light/dark/auto
    notification_preferences: List[NotificationPreference]
    default_model: Optional[str]
    api_rate_limit: Optional[int]
    custom_settings: Dict[str, Any]


@dataclass
class PreferencesUpdateRequest:
    """偏好设置更新请求"""
    language_preference: Optional[str] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    notification_preferences: Optional[List[NotificationPreference]] = None
    default_model: Optional[str] = None
    api_rate_limit: Optional[int] = None
    custom_settings: Optional[Dict[str, Any]] = None


class UserPreferencesPort(ABC):
    """用户偏好设置接口"""
    
    @abstractmethod
    async def get_preferences(self, user_id: int) -> UserPreferences:
        """获取用户偏好设置"""
        pass
    
    @abstractmethod
    async def update_preferences(
        self,
        user_id: int,
        request: PreferencesUpdateRequest
    ) -> UserPreferences:
        """更新用户偏好设置"""
        pass
    
    @abstractmethod
    async def reset_preferences(self, user_id: int) -> UserPreferences:
        """重置为默认设置"""
        pass
    
    @abstractmethod
    async def get_notification_preferences(
        self,
        user_id: int
    ) -> List[NotificationPreference]:
        """获取通知偏好设置"""
        pass
    
    @abstractmethod
    async def update_notification_preference(
        self,
        user_id: int,
        category: NotificationCategory,
        preference: NotificationPreference
    ) -> bool:
        """更新特定类别的通知偏好"""
        pass