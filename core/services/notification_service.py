"""
通知服务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio
import logging

from core.ports.user_preferences import NotificationCategory, NotificationType
from core.services.user_preferences_service import UserPreferencesService
from core.adapters.email.email_service import EmailService
from core.infrastructure.database import AsyncSession


logger = logging.getLogger(__name__)


class NotificationService:
    """通知服务 - 负责根据用户偏好发送各类通知"""
    
    def __init__(
        self,
        session: AsyncSession,
        email_service: Optional[EmailService] = None
    ):
        self.preferences_service = UserPreferencesService(session)
        self.email_service = email_service or EmailService()
        self.session = session
    
    async def send_notification(
        self,
        user_id: int,
        category: NotificationCategory,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = 'normal'
    ) -> Dict[str, bool]:
        """
        发送通知
        返回各渠道发送结果
        """
        # 获取用户通知偏好
        notification_prefs = await self.preferences_service.get_notification_preferences(user_id)
        
        # 找到对应类别的偏好设置
        category_pref = None
        for pref in notification_prefs:
            if pref.category == category:
                category_pref = pref
                break
        
        if not category_pref:
            logger.warning(f"No notification preference found for category {category}")
            return {'email': False, 'in_app': False, 'push': False}
        
        results = {}
        
        # 根据偏好发送通知
        if category_pref.email_enabled:
            results['email'] = await self._send_email_notification(
                user_id, title, content, data
            )
        else:
            results['email'] = False
        
        if category_pref.in_app_enabled:
            results['in_app'] = await self._send_in_app_notification(
                user_id, category, title, content, data, priority
            )
        else:
            results['in_app'] = False
        
        if category_pref.push_enabled:
            results['push'] = await self._send_push_notification(
                user_id, title, content, data
            )
        else:
            results['push'] = False
        
        return results
    
    async def send_batch_notifications(
        self,
        user_ids: List[int],
        category: NotificationCategory,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[int, Dict[str, bool]]:
        """批量发送通知"""
        results = {}
        
        # 使用异步任务并发发送
        tasks = []
        for user_id in user_ids:
            task = self.send_notification(
                user_id, category, title, content, data
            )
            tasks.append((user_id, task))
        
        # 等待所有任务完成
        for user_id, task in tasks:
            try:
                result = await task
                results[user_id] = result
            except Exception as e:
                logger.error(f"Failed to send notification to user {user_id}: {e}")
                results[user_id] = {'email': False, 'in_app': False, 'push': False}
        
        return results
    
    async def _send_email_notification(
        self,
        user_id: int,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """发送邮件通知"""
        try:
            # 获取用户邮箱
            from core.adapters.database.user_repository import UserRepository
            repo = UserRepository(self.session)
            profile = await repo.get_profile(user_id)
            
            if not profile:
                return False
            
            # 发送邮件
            return await self.email_service.send_notification(
                profile.email,
                profile.username,
                'general',
                title,
                content
            )
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def _send_in_app_notification(
        self,
        user_id: int,
        category: NotificationCategory,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        priority: str = 'normal'
    ) -> bool:
        """发送应用内通知"""
        try:
            # 这里应该保存到通知表或推送到消息队列
            # 简化实现：记录到日志
            logger.info(
                f"In-app notification for user {user_id}: "
                f"[{category.value}] {title}"
            )
            
            # TODO: 实际实现应该：
            # 1. 保存到 notifications 表
            # 2. 通过 WebSocket 推送给在线用户
            # 3. 更新未读通知计数
            
            return True
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")
            return False
    
    async def _send_push_notification(
        self,
        user_id: int,
        title: str,
        content: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """发送推送通知"""
        try:
            # 这里应该调用推送服务（如 FCM、APNs）
            # 简化实现：记录到日志
            logger.info(
                f"Push notification for user {user_id}: {title}"
            )
            
            # TODO: 实际实现应该：
            # 1. 获取用户的设备令牌
            # 2. 调用推送服务 API
            # 3. 处理推送结果
            
            return True
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False
    
    async def mark_notification_read(
        self,
        user_id: int,
        notification_id: int
    ) -> bool:
        """标记通知为已读"""
        # TODO: 实现通知已读逻辑
        return True
    
    async def mark_all_notifications_read(
        self,
        user_id: int,
        category: Optional[NotificationCategory] = None
    ) -> int:
        """标记所有通知为已读"""
        # TODO: 实现批量标记已读
        return 0
    
    async def get_unread_count(
        self,
        user_id: int,
        category: Optional[NotificationCategory] = None
    ) -> int:
        """获取未读通知数量"""
        # TODO: 实现未读计数
        return 0
    
    async def delete_old_notifications(
        self,
        days: int = 30
    ) -> int:
        """删除旧通知"""
        # TODO: 实现定期清理
        return 0