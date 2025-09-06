"""
持久化存储服务 - 统一管理数据的存储、缓存和备份
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from core.cache.manager import cache_manager
from core.infrastructure.backup import backup_manager
from core.database.models.analysis import AnalysisTask, AnalysisReport, AnalysisLog
from core.database.models.user import User
from core.database.session import get_db

logger = logging.getLogger(__name__)


class PersistenceService:
    """持久化存储服务"""
    
    def __init__(self):
        self.cache_ttl = {
            "user": 3600,           # 用户信息缓存1小时
            "analysis_task": 1800,  # 分析任务缓存30分钟
            "analysis_report": 7200, # 分析报告缓存2小时
            "market_data": 300,     # 市场数据缓存5分钟
            "statistics": 1800,     # 统计数据缓存30分钟
        }
        
    # ==================== 用户数据管理 ====================
    
    async def get_user_by_id(
        self, 
        user_id: int, 
        use_cache: bool = True,
        db: Optional[AsyncSession] = None
    ) -> Optional[User]:
        """获取用户信息（支持缓存）"""
        cache_key = f"user:{user_id}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_user = await cache_manager.get(cache_key, serialize_method="pickle")
            if cached_user:
                logger.debug(f"从缓存获取用户: {user_id}")
                return cached_user
                
        # 从数据库获取
        if db is None:
            async for session in get_db():
                db = session
                break
                
        try:
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            # 缓存用户信息
            if user and use_cache:
                await cache_manager.set(
                    cache_key, 
                    user, 
                    ttl=self.cache_ttl["user"],
                    serialize_method="pickle"
                )
                logger.debug(f"缓存用户信息: {user_id}")
                
            return user
            
        except Exception as e:
            logger.error(f"获取用户失败 {user_id}: {e}")
            return None
            
    async def invalidate_user_cache(self, user_id: int):
        """清除用户缓存"""
        cache_key = f"user:{user_id}"
        await cache_manager.delete(cache_key)
        logger.debug(f"清除用户缓存: {user_id}")
        
    # ==================== 分析任务管理 ====================
    
    async def get_analysis_task(
        self, 
        task_id: UUID, 
        use_cache: bool = True,
        include_reports: bool = False,
        db: Optional[AsyncSession] = None
    ) -> Optional[AnalysisTask]:
        """获取分析任务（支持缓存）"""
        cache_key = f"analysis_task:{task_id}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_task = await cache_manager.get(cache_key, serialize_method="pickle")
            if cached_task:
                logger.debug(f"从缓存获取分析任务: {task_id}")
                return cached_task
                
        # 从数据库获取
        if db is None:
            async for session in get_db():
                db = session
                break
                
        try:
            query = select(AnalysisTask).where(AnalysisTask.id == task_id)
            
            if include_reports:
                query = query.options(selectinload(AnalysisTask.reports))
                
            result = await db.execute(query)
            task = result.scalar_one_or_none()
            
            # 缓存任务信息
            if task and use_cache:
                await cache_manager.set(
                    cache_key,
                    task,
                    ttl=self.cache_ttl["analysis_task"],
                    serialize_method="pickle"
                )
                logger.debug(f"缓存分析任务: {task_id}")
                
            return task
            
        except Exception as e:
            logger.error(f"获取分析任务失败 {task_id}: {e}")
            return None
            
    async def update_analysis_task_progress(
        self, 
        task_id: UUID, 
        progress: int, 
        status: Optional[str] = None,
        db: Optional[AsyncSession] = None
    ) -> bool:
        """更新分析任务进度"""
        if db is None:
            async for session in get_db():
                db = session
                break
                
        try:
            result = await db.execute(
                select(AnalysisTask).where(AnalysisTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            
            if not task:
                return False
                
            # 更新进度
            task.progress = progress
            task.updated_at = datetime.utcnow()
            
            if status:
                task.status = status
                
            await db.commit()
            
            # 更新缓存
            cache_key = f"analysis_task:{task_id}"
            await cache_manager.set(
                cache_key,
                task,
                ttl=self.cache_ttl["analysis_task"],
                serialize_method="pickle"
            )
            
            # 同时更新实时进度缓存
            progress_key = f"task_progress:{task_id}"
            await cache_manager.set(
                progress_key,
                {
                    "task_id": str(task_id),
                    "progress": progress,
                    "status": status or task.status,
                    "updated_at": datetime.utcnow().isoformat()
                },
                ttl=300  # 5分钟
            )
            
            logger.debug(f"更新任务进度: {task_id} -> {progress}%")
            return True
            
        except Exception as e:
            logger.error(f"更新任务进度失败 {task_id}: {e}")
            return False
            
    async def get_task_progress(self, task_id: UUID) -> Optional[Dict[str, Any]]:
        """获取任务实时进度"""
        progress_key = f"task_progress:{task_id}"
        return await cache_manager.get(progress_key)
        
    async def invalidate_task_cache(self, task_id: UUID):
        """清除任务缓存"""
        cache_key = f"analysis_task:{task_id}"
        progress_key = f"task_progress:{task_id}"
        await cache_manager.delete(cache_key)
        await cache_manager.delete(progress_key)
        logger.debug(f"清除任务缓存: {task_id}")
        
    # ==================== 分析报告管理 ====================
    
    async def get_analysis_reports(
        self,
        task_id: UUID,
        use_cache: bool = True,
        db: Optional[AsyncSession] = None
    ) -> List[AnalysisReport]:
        """获取分析报告列表"""
        cache_key = f"analysis_reports:{task_id}"
        
        # 尝试从缓存获取
        if use_cache:
            cached_reports = await cache_manager.get(cache_key, serialize_method="pickle")
            if cached_reports:
                logger.debug(f"从缓存获取分析报告: {task_id}")
                return cached_reports
                
        # 从数据库获取
        if db is None:
            async for session in get_db():
                db = session
                break
                
        try:
            result = await db.execute(
                select(AnalysisReport)
                .where(AnalysisReport.task_id == task_id)
                .order_by(AnalysisReport.created_at.desc())
            )
            reports = result.scalars().all()
            
            # 缓存报告列表
            if reports and use_cache:
                await cache_manager.set(
                    cache_key,
                    reports,
                    ttl=self.cache_ttl["analysis_report"],
                    serialize_method="pickle"
                )
                logger.debug(f"缓存分析报告: {task_id}")
                
            return reports
            
        except Exception as e:
            logger.error(f"获取分析报告失败 {task_id}: {e}")
            return []
            
    async def cache_analysis_result(
        self,
        task_id: UUID,
        analyst_type: str,
        result: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """缓存分析结果"""
        cache_key = f"analysis_result:{task_id}:{analyst_type}"
        await cache_manager.set(
            cache_key,
            result,
            ttl=ttl or self.cache_ttl["analysis_report"]
        )
        logger.debug(f"缓存分析结果: {task_id} - {analyst_type}")
        
    async def get_cached_analysis_result(
        self,
        task_id: UUID,
        analyst_type: str
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的分析结果"""
        cache_key = f"analysis_result:{task_id}:{analyst_type}"
        return await cache_manager.get(cache_key)
        
    # ==================== 市场数据缓存 ====================
    
    async def cache_market_data(
        self,
        symbol: str,
        market_type: str,
        data: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """缓存市场数据"""
        cache_key = f"market_data:{market_type}:{symbol}"
        await cache_manager.set(
            cache_key,
            {
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
                "symbol": symbol,
                "market_type": market_type
            },
            ttl=ttl or self.cache_ttl["market_data"]
        )
        logger.debug(f"缓存市场数据: {symbol}")
        
    async def get_cached_market_data(
        self,
        symbol: str,
        market_type: str,
        max_age_minutes: int = 5
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的市场数据"""
        cache_key = f"market_data:{market_type}:{symbol}"
        cached_data = await cache_manager.get(cache_key)
        
        if not cached_data:
            return None
            
        # 检查数据是否过期
        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        if datetime.utcnow() - timestamp > timedelta(minutes=max_age_minutes):
            await cache_manager.delete(cache_key)
            return None
            
        return cached_data["data"]
        
    # ==================== 用户统计缓存 ====================
    
    async def cache_user_statistics(
        self,
        user_id: int,
        statistics: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """缓存用户统计数据"""
        cache_key = f"user_stats:{user_id}"
        await cache_manager.set(
            cache_key,
            {
                "statistics": statistics,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id
            },
            ttl=ttl or self.cache_ttl["statistics"]
        )
        logger.debug(f"缓存用户统计: {user_id}")
        
    async def get_cached_user_statistics(
        self,
        user_id: int,
        max_age_minutes: int = 30
    ) -> Optional[Dict[str, Any]]:
        """获取缓存的用户统计数据"""
        cache_key = f"user_stats:{user_id}"
        cached_data = await cache_manager.get(cache_key)
        
        if not cached_data:
            return None
            
        # 检查数据是否过期
        timestamp = datetime.fromisoformat(cached_data["timestamp"])
        if datetime.utcnow() - timestamp > timedelta(minutes=max_age_minutes):
            await cache_manager.delete(cache_key)
            return None
            
        return cached_data["statistics"]
        
    # ==================== 会话管理 ====================
    
    # 认证功能已移除，会话管理临时禁用
    async def store_user_session(
        self,
        user_id: int,
        session_data: Dict[str, Any],
        ttl: int = 86400  # 24小时
    ):
        """存储用户会话数据 - 暂时禁用"""
        pass  # 认证功能已移除
        # session_key = f"session:{user_id}"
        # await cache_manager.set(
        #     session_key,
        #     {
        #         "user_id": user_id,
        #         "data": session_data,
        #         "created_at": datetime.utcnow().isoformat(),
        #         "last_activity": datetime.utcnow().isoformat()
        #     },
        #     ttl=ttl
        # )
        # logger.debug(f"存储用户会话: {user_id}")
        
    async def get_user_session(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户会话数据 - 暂时禁用"""
        return None  # 认证功能已移除
        # session_key = f"session:{user_id}"
        # session_data = await cache_manager.get(session_key)
        # 
        # if session_data:
        #     # 更新最后活动时间
        #     session_data["last_activity"] = datetime.utcnow().isoformat()
        #     await cache_manager.set(session_key, session_data, ttl=86400)
        #     
        # return session_data
        
    async def invalidate_user_session(self, user_id: int):
        """清除用户会话 - 暂时禁用"""
        pass  # 认证功能已移除
        # session_key = f"session:{user_id}"
        # await cache_manager.delete(session_key)
        # logger.debug(f"清除用户会话: {user_id}")
        
    # ==================== 批量操作 ====================
    
    async def batch_cache_tasks(
        self,
        tasks: List[AnalysisTask],
        ttl: Optional[int] = None
    ):
        """批量缓存分析任务"""
        for task in tasks:
            cache_key = f"analysis_task:{task.id}"
            await cache_manager.set(
                cache_key,
                task,
                ttl=ttl or self.cache_ttl["analysis_task"],
                serialize_method="pickle"
            )
        logger.debug(f"批量缓存任务: {len(tasks)}个")
        
    async def batch_invalidate_user_cache(self, user_ids: List[int]):
        """批量清除用户缓存"""
        cache_keys = [f"user:{user_id}" for user_id in user_ids]
        for cache_key in cache_keys:
            await cache_manager.delete(cache_key)
        logger.debug(f"批量清除用户缓存: {len(user_ids)}个")
        
    # ==================== 缓存统计和监控 ====================
    
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        try:
            stats = await cache_manager.get_cache_stats()
            
            # 添加应用级统计
            app_stats = {
                "cache_keys_by_type": {},
                "total_app_keys": 0
            }
            
            # 统计不同类型的缓存键数量
            if cache_manager.redis_client:
                keys = await cache_manager.redis_client.keys(f"{cache_manager.prefix}*")
                app_stats["total_app_keys"] = len(keys)
                
                key_types = {}
                for key in keys:
                    key_str = key.decode('utf-8')
                    key_type = key_str.split(':')[1] if ':' in key_str else 'unknown'
                    key_types[key_type] = key_types.get(key_type, 0) + 1
                    
                app_stats["cache_keys_by_type"] = key_types
                
            stats.update(app_stats)
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {e}")
            return {}
            
    async def warm_up_cache(self, user_id: int, db: AsyncSession):
        """预热缓存 - 为用户预加载常用数据"""
        try:
            # 预加载用户信息
            await self.get_user_by_id(user_id, use_cache=True, db=db)
            
            # 预加载用户最近的任务
            result = await db.execute(
                select(AnalysisTask)
                .where(AnalysisTask.user_id == user_id)
                .order_by(AnalysisTask.created_at.desc())
                .limit(10)
            )
            recent_tasks = result.scalars().all()
            await self.batch_cache_tasks(recent_tasks)
            
            logger.info(f"缓存预热完成: 用户 {user_id}")
            
        except Exception as e:
            logger.error(f"缓存预热失败 {user_id}: {e}")
            
    async def cleanup_expired_cache(self):
        """清理过期缓存"""
        try:
            # Redis会自动处理TTL过期，这里可以添加应用级清理逻辑
            logger.info("缓存清理完成")
            
        except Exception as e:
            logger.error(f"缓存清理失败: {e}")
            
    # ==================== 数据一致性保证 ====================
    
    async def sync_cache_with_db(
        self,
        model_type: str,
        model_id: Union[int, UUID],
        db: AsyncSession
    ):
        """同步缓存与数据库数据"""
        try:
            if model_type == "user":
                # 从数据库重新加载用户数据并更新缓存
                result = await db.execute(select(User).where(User.id == model_id))
                user = result.scalar_one_or_none()
                if user:
                    cache_key = f"user:{model_id}"
                    await cache_manager.set(
                        cache_key,
                        user,
                        ttl=self.cache_ttl["user"],
                        serialize_method="pickle"
                    )
                    
            elif model_type == "analysis_task":
                # 重新加载任务数据
                result = await db.execute(
                    select(AnalysisTask).where(AnalysisTask.id == model_id)
                )
                task = result.scalar_one_or_none()
                if task:
                    cache_key = f"analysis_task:{model_id}"
                    await cache_manager.set(
                        cache_key,
                        task,
                        ttl=self.cache_ttl["analysis_task"],
                        serialize_method="pickle"
                    )
                    
            logger.debug(f"数据同步完成: {model_type}:{model_id}")
            
        except Exception as e:
            logger.error(f"数据同步失败 {model_type}:{model_id}: {e}")


# 全局持久化服务实例
persistence_service = PersistenceService()