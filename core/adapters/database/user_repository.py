"""
用户数据存储适配器
"""
from typing import Optional, List
from datetime import datetime
from sqlalchemy import select, update, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession
import hashlib
import secrets

from core.ports.user_profile import UserProfilePort, UserProfile, ProfileUpdateRequest, AvatarUploadResult
from core.ports.security_settings import (
    SecuritySettingsPort, SecuritySettings, PasswordChangeRequest,
    UserSession, LoginHistory, ApiKey, TwoFactorSetupResult
)
from core.database.models import User
from core.database.models.account import (
    UserSession as UserSessionModel,
    LoginHistory as LoginHistoryModel,
    ApiKey as ApiKeyModel
)


class UserRepository(UserProfilePort, SecuritySettingsPort):
    """用户数据存储适配器，实现用户资料和安全设置接口"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    # UserProfilePort 实现
    async def get_profile(self, user_id: int) -> Optional[UserProfile]:
        """获取用户资料"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
            
        return UserProfile(
            user_id=user.id,
            email=user.email,
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            bio=user.bio,
            language_preference=user.language,
            timezone=user.timezone,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login_at,
            email_verified=user.email_verified
        )
    
    async def update_profile(
        self,
        user_id: int,
        request: ProfileUpdateRequest
    ) -> UserProfile:
        """更新用户资料"""
        update_data = {}
        if request.display_name is not None:
            update_data['display_name'] = request.display_name
        if request.bio is not None:
            update_data['bio'] = request.bio
        if request.language_preference is not None:
            update_data['language'] = request.language_preference
        if request.timezone is not None:
            update_data['timezone'] = request.timezone
            
        if update_data:
            await self.session.execute(
                update(User).where(User.id == user_id).values(**update_data)
            )
            await self.session.commit()
            
        profile = await self.get_profile(user_id)
        if not profile:
            raise ValueError("User not found")
        return profile
    
    async def upload_avatar(
        self,
        user_id: int,
        file_data: bytes,
        file_name: str,
        mime_type: str
    ) -> AvatarUploadResult:
        """上传头像 - 这里只更新URL，实际存储由storage adapter处理"""
        # 生成唯一的文件名
        file_hash = hashlib.md5(file_data).hexdigest()
        avatar_url = f"/avatars/{user_id}/{file_hash}_{file_name}"
        
        await self.session.execute(
            update(User).where(User.id == user_id).values(avatar_url=avatar_url)
        )
        await self.session.commit()
        
        return AvatarUploadResult(
            avatar_url=avatar_url,
            file_size=len(file_data),
            mime_type=mime_type
        )
    
    async def delete_avatar(self, user_id: int) -> bool:
        """删除头像"""
        await self.session.execute(
            update(User).where(User.id == user_id).values(avatar_url=None)
        )
        await self.session.commit()
        return True
    
    async def verify_email(self, user_id: int, token: str) -> bool:
        """验证邮箱"""
        # 实际实现中应该验证token
        await self.session.execute(
            update(User).where(User.id == user_id).values(email_verified=True)
        )
        await self.session.commit()
        return True
    
    async def get_profile_by_username(
        self,
        username: str
    ) -> Optional[UserProfile]:
        """通过用户名获取资料"""
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
            
        return await self.get_profile(user.id)
    
    # SecuritySettingsPort 实现
    async def get_security_settings(self, user_id: int) -> SecuritySettings:
        """获取安全设置汇总"""
        # 获取用户信息
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("User not found")
        
        # 统计活跃会话
        session_count_result = await self.session.execute(
            select(UserSessionModel).where(
                and_(
                    UserSessionModel.user_id == user_id,
                    UserSessionModel.is_active == True
                )
            )
        )
        active_sessions_count = len(session_count_result.scalars().all())
        
        # 统计API密钥
        api_key_count_result = await self.session.execute(
            select(ApiKeyModel).where(
                and_(
                    ApiKeyModel.user_id == user_id,
                    ApiKeyModel.is_active == True
                )
            )
        )
        api_keys_count = len(api_key_count_result.scalars().all())
        
        return SecuritySettings(
            two_factor_enabled=user.two_factor_enabled,
            last_password_change=user.last_password_change,
            active_sessions_count=active_sessions_count,
            api_keys_count=api_keys_count,
            suspicious_activity_detected=False  # 需要实际的检测逻辑
        )
    
    async def change_password(
        self,
        user_id: int,
        request: PasswordChangeRequest
    ) -> bool:
        """修改密码"""
        # 实际实现中需要验证当前密码并加密新密码
        # 这里简化处理
        await self.session.execute(
            update(User).where(User.id == user_id).values(
                last_password_change=datetime.utcnow()
            )
        )
        await self.session.commit()
        return True
    
    async def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """获取活跃会话"""
        result = await self.session.execute(
            select(UserSessionModel).where(
                and_(
                    UserSessionModel.user_id == user_id,
                    UserSessionModel.is_active == True
                )
            ).order_by(UserSessionModel.last_activity.desc())
        )
        sessions = result.scalars().all()
        
        return [
            UserSession(
                id=s.id,
                user_id=s.user_id,
                session_token=s.session_token,
                ip_address=s.ip_address,
                user_agent=s.user_agent,
                created_at=s.created_at,
                last_activity=s.last_activity,
                is_active=s.is_active,
                status="active"
            )
            for s in sessions
        ]
    
    async def revoke_session(self, user_id: int, session_id: int) -> bool:
        """撤销会话"""
        result = await self.session.execute(
            update(UserSessionModel).where(
                and_(
                    UserSessionModel.id == session_id,
                    UserSessionModel.user_id == user_id
                )
            ).values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0
    
    async def revoke_all_sessions(self, user_id: int) -> int:
        """撤销所有会话"""
        result = await self.session.execute(
            update(UserSessionModel).where(
                and_(
                    UserSessionModel.user_id == user_id,
                    UserSessionModel.is_active == True
                )
            ).values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount
    
    async def get_login_history(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[LoginHistory]:
        """获取登录历史"""
        result = await self.session.execute(
            select(LoginHistoryModel).where(
                LoginHistoryModel.user_id == user_id
            ).order_by(LoginHistoryModel.login_time.desc()).limit(limit)
        )
        history = result.scalars().all()
        
        return [
            LoginHistory(
                id=h.id,
                user_id=h.user_id,
                ip_address=h.ip_address,
                user_agent=h.user_agent,
                login_time=h.login_time,
                success=h.success,
                failure_reason=h.failure_reason
            )
            for h in history
        ]
    
    async def setup_two_factor(self, user_id: int) -> TwoFactorSetupResult:
        """设置双因素认证"""
        # 生成密钥
        secret = secrets.token_urlsafe(32)
        
        # 保存密钥
        await self.session.execute(
            update(User).where(User.id == user_id).values(
                two_factor_secret=secret
            )
        )
        await self.session.commit()
        
        # 生成备份码
        backup_codes = [secrets.token_hex(4) for _ in range(8)]
        
        return TwoFactorSetupResult(
            secret=secret,
            qr_code_url=f"otpauth://totp/WhenTrade:{user_id}?secret={secret}",
            backup_codes=backup_codes
        )
    
    async def verify_two_factor(
        self,
        user_id: int,
        code: str
    ) -> bool:
        """验证双因素认证码"""
        # 实际实现中需要验证TOTP码
        return True
    
    async def disable_two_factor(
        self,
        user_id: int,
        password: str
    ) -> bool:
        """禁用双因素认证"""
        # 实际实现中需要验证密码
        await self.session.execute(
            update(User).where(User.id == user_id).values(
                two_factor_enabled=False,
                two_factor_secret=None
            )
        )
        await self.session.commit()
        return True
    
    async def get_api_keys(self, user_id: int) -> List[ApiKey]:
        """获取API密钥列表"""
        result = await self.session.execute(
            select(ApiKeyModel).where(
                ApiKeyModel.user_id == user_id
            ).order_by(ApiKeyModel.created_at.desc())
        )
        keys = result.scalars().all()
        
        return [
            ApiKey(
                id=k.id,
                user_id=k.user_id,
                name=k.name,
                key_prefix=k.key_hash[:8],  # 显示前缀
                permissions=k.permissions,
                last_used=k.last_used,
                created_at=k.created_at,
                expires_at=k.expires_at,
                is_active=k.is_active
            )
            for k in keys
        ]
    
    async def create_api_key(
        self,
        user_id: int,
        name: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[ApiKey, str]:
        """创建API密钥"""
        # 生成密钥
        api_key = secrets.token_urlsafe(32)
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # 保存到数据库
        new_key = ApiKeyModel(
            user_id=user_id,
            key_hash=key_hash,
            name=name,
            permissions=permissions,
            expires_at=expires_at
        )
        self.session.add(new_key)
        await self.session.commit()
        
        api_key_info = ApiKey(
            id=new_key.id,
            user_id=new_key.user_id,
            name=new_key.name,
            key_prefix=key_hash[:8],
            permissions=new_key.permissions,
            last_used=new_key.last_used,
            created_at=new_key.created_at,
            expires_at=new_key.expires_at,
            is_active=new_key.is_active
        )
        
        return api_key_info, api_key
    
    async def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        """撤销API密钥"""
        result = await self.session.execute(
            update(ApiKeyModel).where(
                and_(
                    ApiKeyModel.id == key_id,
                    ApiKeyModel.user_id == user_id
                )
            ).values(is_active=False)
        )
        await self.session.commit()
        return result.rowcount > 0