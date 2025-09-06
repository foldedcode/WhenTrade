"""
安全设置服务
"""
from typing import List, Optional
from datetime import datetime
import bcrypt

from core.ports.security_settings import (
    SecuritySettingsPort, SecuritySettings, PasswordChangeRequest,
    UserSession, LoginHistory, ApiKey, TwoFactorSetupResult
)
from core.adapters.database.user_repository import UserRepository
from core.adapters.email.email_service import EmailService
from core.infrastructure.database import AsyncSession
from core.database.models.account import LoginHistory as LoginHistoryModel


class SecurityService:
    """安全设置服务"""
    
    def __init__(
        self,
        session: AsyncSession,
        email_service: Optional[EmailService] = None
    ):
        self.repository = UserRepository(session)
        self.session = session
        self.email_service = email_service or EmailService()
    
    async def get_security_settings(self, user_id: int) -> SecuritySettings:
        """获取安全设置汇总"""
        return await self.repository.get_security_settings(user_id)
    
    async def change_password(
        self,
        user_id: int,
        request: PasswordChangeRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """修改密码"""
        # 获取用户资料
        profile = await self.repository.get_profile(user_id)
        if not profile:
            raise ValueError("用户不存在")
        
        # 这里应该验证当前密码，但简化处理
        # 实际实现中需要从数据库获取密码哈希并验证
        
        # 更新密码
        result = await self.repository.change_password(user_id, request)
        
        if result:
            # 记录密码修改历史
            await self._log_security_event(
                user_id,
                'password_changed',
                True,
                ip_address,
                user_agent
            )
            
            # 发送安全提醒邮件
            await self.email_service.send_security_alert(
                profile.email,
                profile.username,
                'password_changed',
                {
                    'ip_address': ip_address or '未知',
                    'user_agent': user_agent or '未知'
                }
            )
            
            # 撤销所有现有会话（除当前会话外）
            await self.repository.revoke_all_sessions(user_id)
        
        return result
    
    async def get_active_sessions(self, user_id: int) -> List[UserSession]:
        """获取活跃会话"""
        return await self.repository.get_active_sessions(user_id)
    
    async def revoke_session(self, user_id: int, session_id: int) -> bool:
        """撤销会话"""
        return await self.repository.revoke_session(user_id, session_id)
    
    async def revoke_all_sessions(
        self,
        user_id: int,
        except_current: Optional[str] = None
    ) -> int:
        """撤销所有会话"""
        # 如果提供了当前会话token，保留它
        if except_current:
            # 获取所有会话
            sessions = await self.get_active_sessions(user_id)
            revoked_count = 0
            
            for session in sessions:
                if session.session_token != except_current:
                    if await self.revoke_session(user_id, session.id):
                        revoked_count += 1
            
            return revoked_count
        else:
            return await self.repository.revoke_all_sessions(user_id)
    
    async def get_login_history(
        self,
        user_id: int,
        limit: int = 20
    ) -> List[LoginHistory]:
        """获取登录历史"""
        return await self.repository.get_login_history(user_id, limit)
    
    async def record_login_attempt(
        self,
        user_id: int,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        failure_reason: Optional[str] = None
    ) -> None:
        """记录登录尝试"""
        login_record = LoginHistoryModel(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            failure_reason=failure_reason
        )
        self.session.add(login_record)
        await self.session.commit()
        
        # 如果登录失败次数过多，发送安全提醒
        if not success:
            await self._check_suspicious_activity(user_id)
    
    async def setup_two_factor(self, user_id: int) -> TwoFactorSetupResult:
        """设置双因素认证"""
        # 获取用户资料
        profile = await self.repository.get_profile(user_id)
        if not profile:
            raise ValueError("用户不存在")
        
        result = await self.repository.setup_two_factor(user_id)
        
        # 发送安全提醒
        await self.email_service.send_security_alert(
            profile.email,
            profile.username,
            'two_factor_enabled',
            {}
        )
        
        return result
    
    async def verify_two_factor(
        self,
        user_id: int,
        code: str
    ) -> bool:
        """验证双因素认证码"""
        return await self.repository.verify_two_factor(user_id, code)
    
    async def disable_two_factor(
        self,
        user_id: int,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> bool:
        """禁用双因素认证"""
        # 获取用户资料
        profile = await self.repository.get_profile(user_id)
        if not profile:
            raise ValueError("用户不存在")
        
        result = await self.repository.disable_two_factor(user_id, password)
        
        if result:
            # 记录事件
            await self._log_security_event(
                user_id,
                'two_factor_disabled',
                True,
                ip_address,
                user_agent
            )
            
            # 发送安全提醒
            await self.email_service.send_security_alert(
                profile.email,
                profile.username,
                'two_factor_disabled',
                {
                    'ip_address': ip_address or '未知',
                    'user_agent': user_agent or '未知'
                }
            )
        
        return result
    
    async def get_api_keys(self, user_id: int) -> List[ApiKey]:
        """获取API密钥列表"""
        return await self.repository.get_api_keys(user_id)
    
    async def create_api_key(
        self,
        user_id: int,
        name: str,
        permissions: List[str],
        expires_at: Optional[datetime] = None
    ) -> tuple[ApiKey, str]:
        """创建API密钥"""
        # 验证权限
        valid_permissions = [
            'read:profile', 'write:profile',
            'read:analysis', 'write:analysis',
            'read:trading', 'write:trading'
        ]
        
        for perm in permissions:
            if perm not in valid_permissions:
                raise ValueError(f"无效的权限: {perm}")
        
        # 获取用户资料
        profile = await self.repository.get_profile(user_id)
        if not profile:
            raise ValueError("用户不存在")
        
        # 创建密钥
        key_info, api_key = await self.repository.create_api_key(
            user_id, name, permissions, expires_at
        )
        
        # 发送安全提醒
        await self.email_service.send_security_alert(
            profile.email,
            profile.username,
            'api_key_created',
            {'key_name': name}
        )
        
        return key_info, api_key
    
    async def revoke_api_key(self, user_id: int, key_id: int) -> bool:
        """撤销API密钥"""
        return await self.repository.revoke_api_key(user_id, key_id)
    
    async def _log_security_event(
        self,
        user_id: int,
        event_type: str,
        success: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """记录安全事件"""
        # 这里可以记录到专门的安全日志表
        # 简化处理，记录到登录历史
        await self.record_login_attempt(
            user_id,
            success,
            ip_address,
            user_agent,
            event_type if not success else None
        )
    
    async def _check_suspicious_activity(self, user_id: int) -> None:
        """检查可疑活动"""
        # 获取最近的登录失败记录
        history = await self.get_login_history(user_id, 10)
        
        # 统计最近1小时内的失败次数
        recent_failures = 0
        one_hour_ago = datetime.utcnow().replace(hour=datetime.utcnow().hour - 1)
        
        for record in history:
            if not record.success and record.login_time > one_hour_ago:
                recent_failures += 1
        
        # 如果失败次数过多，发送警告
        if recent_failures >= 5:
            profile = await self.repository.get_profile(user_id)
            if profile:
                await self.email_service.send_security_alert(
                    profile.email,
                    profile.username,
                    'suspicious_activity',
                    {'failed_attempts': recent_failures}
                )
    
    async def generate_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    async def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))