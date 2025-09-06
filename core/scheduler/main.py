"""
主调度器服务
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import json

from core.database import get_db
from core.config import settings
import redis.asyncio as redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.redis_client = None
        self.running = False
        self.tasks = {}
        
    async def initialize(self):
        """初始化调度器"""
        try:
            redis_url = getattr(settings, 'REDIS_URL', None) or 'redis://redis:6379/0'
            self.redis_client = await redis.from_url(redis_url)
            logger.info("Task scheduler initialized")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            raise
            
    async def register_task(self, name: str, cron: str, handler: callable):
        """注册定时任务"""
        self.tasks[name] = {
            'cron': cron,
            'handler': handler,
            'last_run': None
        }
        logger.info(f"Registered task: {name} with cron: {cron}")
        
    async def run_task(self, name: str):
        """运行单个任务"""
        task = self.tasks.get(name)
        if not task:
            logger.error(f"Task {name} not found")
            return
            
        try:
            logger.info(f"Running task: {name}")
            await task['handler']()
            task['last_run'] = datetime.utcnow()
            
            # 记录到Redis
            if self.redis_client:
                await self.redis_client.hset(
                    'scheduler:tasks',
                    name,
                    json.dumps({
                        'last_run': task['last_run'].isoformat(),
                        'status': 'success'
                    })
                )
                
        except Exception as e:
            logger.error(f"Error running task {name}: {e}")
            
            # 记录错误到Redis
            if self.redis_client:
                await self.redis_client.hset(
                    'scheduler:tasks',
                    name,
                    json.dumps({
                        'last_run': datetime.utcnow().isoformat(),
                        'status': 'error',
                        'error': str(e)
                    })
                )
                
    async def start(self):
        """启动调度器"""
        self.running = True
        logger.info("Task scheduler started")
        
        # 注册默认任务
        await self._register_default_tasks()
        
        # 主循环
        while self.running:
            try:
                # 每分钟检查一次任务
                current_time = datetime.utcnow()
                
                for name, task in self.tasks.items():
                    # 简单的调度逻辑，实际应该使用cron解析
                    if self._should_run_task(name, current_time):
                        asyncio.create_task(self.run_task(name))
                        
                # 等待下一分钟
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(10)
                
    async def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("Task scheduler stopped")
        
    def _should_run_task(self, name: str, current_time: datetime) -> bool:
        """判断任务是否应该运行"""
        task = self.tasks.get(name)
        if not task:
            return False
            
        # 简单的实现：如果超过1小时没运行，就运行
        if not task['last_run']:
            return True
            
        time_since_last_run = current_time - task['last_run']
        return time_since_last_run > timedelta(hours=1)
        
    async def _register_default_tasks(self):
        """注册默认任务"""
        # 清理过期缓存
        async def cleanup_cache():
            try:
                if self.redis_client:
                    # 清理过期的缓存键
                    logger.info("Running cache cleanup task")
                    # 实际实现需要更复杂的逻辑
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                
        await self.register_task('cleanup_cache', '0 * * * *', cleanup_cache)
        
        # 系统健康检查
        async def health_check():
            try:
                logger.info("Running system health check")
                # 检查数据库连接
                async for session in get_db():
                    await session.execute(select(1))
                    
                # 检查Redis连接
                if self.redis_client:
                    await self.redis_client.ping()
                    
                logger.info("System health check passed")
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                
        await self.register_task('health_check', '*/5 * * * *', health_check)


# 全局调度器实例
scheduler = TaskScheduler()


async def run_scheduler():
    """运行调度器的主函数"""
    try:
        await scheduler.initialize()
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        await scheduler.stop()
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
        raise


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行调度器
    asyncio.run(run_scheduler())