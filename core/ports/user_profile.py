"""
用户资料管理接口定义
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class UserProfile:
    """用户资料数据模型"""
    user_id: int
    email: str
    username: str
    display_name: Optional[str]
    avatar_url: Optional[str]
    bio: Optional[str]
    language_preference: str
    timezone: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    email_verified: bool


@dataclass
class ProfileUpdateRequest:
    """资料更新请求"""
    display_name: Optional[str] = None
    bio: Optional[str] = None
    language_preference: Optional[str] = None
    timezone: Optional[str] = None


@dataclass
class AvatarUploadResult:
    """头像上传结果"""
    avatar_url: str
    file_size: int
    mime_type: str


class UserProfilePort(ABC):
    """用户资料管理接口"""
    
    @abstractmethod
    async def get_profile(self, user_id: int) -> Optional[UserProfile]:
        """获取用户资料"""
        pass
    
    @abstractmethod
    async def update_profile(
        self,
        user_id: int,
        request: ProfileUpdateRequest
    ) -> UserProfile:
        """更新用户资料"""
        pass
    
    @abstractmethod
    async def upload_avatar(
        self,
        user_id: int,
        file_data: bytes,
        file_name: str,
        mime_type: str
    ) -> AvatarUploadResult:
        """上传头像"""
        pass
    
    @abstractmethod
    async def delete_avatar(self, user_id: int) -> bool:
        """删除头像"""
        pass
    
    @abstractmethod
    async def verify_email(self, user_id: int, token: str) -> bool:
        """验证邮箱"""
        pass
    
    @abstractmethod
    async def get_profile_by_username(
        self,
        username: str
    ) -> Optional[UserProfile]:
        """通过用户名获取资料"""
        pass