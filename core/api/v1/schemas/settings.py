"""
设置相关的 Pydantic 模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class NotificationChannel(str, Enum):
    """通知渠道枚举"""
    EMAIL = "email"
    IN_APP = "in_app"
    PUSH = "push"


class NotificationCategoryEnum(str, Enum):
    """通知类别枚举"""
    SECURITY = "security"
    ACCOUNT = "account"
    TRADING = "trading"
    COST_ALERT = "cost_alert"
    ACHIEVEMENT = "achievement"
    SYSTEM = "system"


class NotificationPreferenceSchema(BaseModel):
    """通知偏好设置模型"""
    category: NotificationCategoryEnum
    email_enabled: bool = True
    in_app_enabled: bool = True
    push_enabled: bool = False


class UserPreferencesResponse(BaseModel):
    """用户偏好设置响应模型"""
    user_id: str
    language_preference: str = "zh"
    timezone: str = "Asia/Shanghai"
    theme: str = "light"
    notification_preferences: List[NotificationPreferenceSchema]
    default_model: Optional[str] = None
    api_rate_limit: Optional[int] = None
    custom_settings: Dict[str, Any] = {}


class PreferencesUpdateRequest(BaseModel):
    """偏好设置更新请求模型"""
    language_preference: Optional[str] = Field(None, pattern="^(zh|en)$")
    timezone: Optional[str] = None
    theme: Optional[str] = Field(None, pattern="^(light|dark|auto)$")
    notification_preferences: Optional[List[NotificationPreferenceSchema]] = None
    default_model: Optional[str] = None
    api_rate_limit: Optional[int] = Field(None, ge=0, le=1000)
    custom_settings: Optional[Dict[str, Any]] = None


class SecuritySettingsResponse(BaseModel):
    """安全设置响应模型"""
    two_factor_enabled: bool = False
    last_password_change: Optional[datetime] = None
    active_sessions_count: int = 0
    api_keys_count: int = 0
    suspicious_activity_detected: bool = False


class UserSessionResponse(BaseModel):
    """用户会话响应模型"""
    id: int
    session_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    last_activity: datetime
    is_active: bool = True
    status: str = "active"


class LoginHistoryResponse(BaseModel):
    """登录历史响应模型"""
    id: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    login_time: datetime
    success: bool
    failure_reason: Optional[str] = None


class ApiKeyResponse(BaseModel):
    """API密钥响应模型（不包含完整密钥）"""
    id: int
    name: str
    key_prefix: str = Field(..., description="密钥前缀，用于识别")
    permissions: List[str]
    last_used: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool = True


class ApiKeyCreateRequest(BaseModel):
    """创建API密钥请求模型"""
    name: str = Field(..., min_length=1, max_length=100)
    permissions: List[str] = Field(..., min_items=1)
    expires_at: Optional[datetime] = None
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v):
        valid_permissions = {
            'read:profile', 'write:profile',
            'read:analysis', 'write:analysis',
            'read:trading', 'write:trading'
        }
        for perm in v:
            if perm not in valid_permissions:
                raise ValueError(f"无效的权限: {perm}")
        return v


class ApiKeyCreateResponse(BaseModel):
    """创建API密钥响应模型"""
    key_info: ApiKeyResponse
    api_key: str = Field(..., description="完整的API密钥，仅在创建时返回一次")


class PasswordChangeRequest(BaseModel):
    """密码修改请求模型"""
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    
    @field_validator('new_password')
    @classmethod
    def validate_new_password(cls, v, info=None):
        if info and info.data and 'current_password' in info.data and v == info.data['current_password']:
            raise ValueError("新密码不能与当前密码相同")
        
        # 密码强度验证
        if not any(c.isupper() for c in v):
            raise ValueError("密码必须包含至少一个大写字母")
        if not any(c.islower() for c in v):
            raise ValueError("密码必须包含至少一个小写字母")
        if not any(c.isdigit() for c in v):
            raise ValueError("密码必须包含至少一个数字")
        
        return v


class EmailChangeRequest(BaseModel):
    """邮箱修改请求模型"""
    new_email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)


class TwoFactorSetupResponse(BaseModel):
    """双因素认证设置响应模型"""
    secret: str
    qr_code_url: str
    backup_codes: List[str]


class TwoFactorVerifyRequest(BaseModel):
    """双因素认证验证请求模型"""
    code: str = Field(..., pattern=r'^\d{6}$')


class TwoFactorDisableRequest(BaseModel):
    """禁用双因素认证请求模型"""
    password: str = Field(..., min_length=8)