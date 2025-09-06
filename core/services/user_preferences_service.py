"""
用户偏好设置服务
"""
from typing import List, Dict, Any
from sqlalchemy import select, update

from core.ports.user_preferences import (
    UserPreferencesPort, UserPreferences, PreferencesUpdateRequest,
    NotificationPreference, NotificationCategory, NotificationType
)
from core.database.models import User
from core.infrastructure.database import AsyncSession


class UserPreferencesService(UserPreferencesPort):
    """用户偏好设置服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_preferences(self, user_id: int) -> UserPreferences:
        """获取用户偏好设置"""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("用户不存在")
        
        # 从用户模型构建偏好设置
        notification_prefs = self._parse_notification_preferences(
            user.notification_preferences or {}
        )
        
        custom_settings = user.preferences or {}
        
        return UserPreferences(
            user_id=user.id,
            language_preference=user.language,
            timezone=user.timezone,
            theme=custom_settings.get('theme', 'light'),
            notification_preferences=notification_prefs,
            default_model=custom_settings.get('default_model'),
            api_rate_limit=custom_settings.get('api_rate_limit'),
            custom_settings=custom_settings
        )
    
    async def update_preferences(
        self,
        user_id: int,
        request: PreferencesUpdateRequest
    ) -> UserPreferences:
        """更新用户偏好设置"""
        # 获取当前用户
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError("用户不存在")
        
        # 准备更新数据
        update_data = {}
        custom_settings = user.preferences or {}
        
        if request.language_preference is not None:
            update_data['language'] = request.language_preference
        
        if request.timezone is not None:
            update_data['timezone'] = request.timezone
        
        if request.theme is not None:
            custom_settings['theme'] = request.theme
        
        if request.default_model is not None:
            custom_settings['default_model'] = request.default_model
        
        if request.api_rate_limit is not None:
            custom_settings['api_rate_limit'] = request.api_rate_limit
        
        if request.custom_settings is not None:
            custom_settings.update(request.custom_settings)
        
        # 处理通知偏好
        if request.notification_preferences is not None:
            notification_dict = self._notification_preferences_to_dict(
                request.notification_preferences
            )
            update_data['notification_preferences'] = notification_dict
        
        # 更新自定义设置
        if custom_settings != user.preferences:
            update_data['preferences'] = custom_settings
        
        # 执行更新
        if update_data:
            await self.session.execute(
                update(User).where(User.id == user_id).values(**update_data)
            )
            await self.session.commit()
        
        # 返回更新后的偏好设置
        return await self.get_preferences(user_id)
    
    async def reset_preferences(self, user_id: int) -> UserPreferences:
        """重置为默认设置"""
        # 获取默认通知偏好
        default_notification_prefs = self._get_default_notification_preferences()
        
        # 重置请求
        reset_request = PreferencesUpdateRequest(
            language_preference='zh',
            timezone='Asia/Shanghai',
            theme='light',
            notification_preferences=default_notification_prefs,
            default_model=None,
            api_rate_limit=None,
            custom_settings={}
        )
        
        return await self.update_preferences(user_id, reset_request)
    
    async def get_notification_preferences(
        self,
        user_id: int
    ) -> List[NotificationPreference]:
        """获取通知偏好设置"""
        preferences = await self.get_preferences(user_id)
        return preferences.notification_preferences
    
    async def update_notification_preference(
        self,
        user_id: int,
        category: NotificationCategory,
        preference: NotificationPreference
    ) -> bool:
        """更新特定类别的通知偏好"""
        # 获取当前偏好
        current_prefs = await self.get_notification_preferences(user_id)
        
        # 更新指定类别
        updated_prefs = []
        found = False
        
        for pref in current_prefs:
            if pref.category == category:
                updated_prefs.append(preference)
                found = True
            else:
                updated_prefs.append(pref)
        
        # 如果类别不存在，添加新的
        if not found:
            updated_prefs.append(preference)
        
        # 更新偏好设置
        update_request = PreferencesUpdateRequest(
            notification_preferences=updated_prefs
        )
        
        await self.update_preferences(user_id, update_request)
        return True
    
    def _parse_notification_preferences(
        self,
        pref_dict: Dict[str, Any]
    ) -> List[NotificationPreference]:
        """解析通知偏好字典"""
        preferences = []
        
        # 如果是空字典，返回默认设置
        if not pref_dict:
            return self._get_default_notification_preferences()
        
        # 解析每个类别的设置
        for category in NotificationCategory:
            category_settings = pref_dict.get(category.value, {})
            
            preference = NotificationPreference(
                category=category,
                email_enabled=category_settings.get('email', True),
                in_app_enabled=category_settings.get('in_app', True),
                push_enabled=category_settings.get('push', False)
            )
            preferences.append(preference)
        
        return preferences
    
    def _notification_preferences_to_dict(
        self,
        preferences: List[NotificationPreference]
    ) -> Dict[str, Any]:
        """将通知偏好列表转换为字典"""
        pref_dict = {}
        
        for pref in preferences:
            pref_dict[pref.category.value] = {
                'email': pref.email_enabled,
                'in_app': pref.in_app_enabled,
                'push': pref.push_enabled
            }
        
        return pref_dict
    
    def _get_default_notification_preferences(self) -> List[NotificationPreference]:
        """获取默认通知偏好设置"""
        defaults = [
            # 安全通知默认全部开启
            NotificationPreference(
                category=NotificationCategory.SECURITY,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=True
            ),
            # 账户通知
            NotificationPreference(
                category=NotificationCategory.ACCOUNT,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=False
            ),
            # 交易通知
            NotificationPreference(
                category=NotificationCategory.TRADING,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=True
            ),
            # 成本提醒
            NotificationPreference(
                category=NotificationCategory.COST_ALERT,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=False
            ),
            # 成就通知
            NotificationPreference(
                category=NotificationCategory.ACHIEVEMENT,
                email_enabled=False,
                in_app_enabled=True,
                push_enabled=False
            ),
            # 系统通知
            NotificationPreference(
                category=NotificationCategory.SYSTEM,
                email_enabled=True,
                in_app_enabled=True,
                push_enabled=False
            )
        ]
        
        return defaults