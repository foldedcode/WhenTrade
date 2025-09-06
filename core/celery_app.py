"""
Celery配置和应用实例
"""
from celery import Celery
from celery.schedules import crontab
from core.config import settings

# 创建Celery应用实例
# 使用CELERY_BROKER_URL和CELERY_RESULT_BACKEND，如果没有则使用REDIS_URL
broker_url = getattr(settings, 'CELERY_BROKER_URL', None) or getattr(settings, 'REDIS_URL', None) or 'redis://redis:6379/0'
result_backend = getattr(settings, 'CELERY_RESULT_BACKEND', None) or getattr(settings, 'REDIS_URL', None) or 'redis://redis:6379/0'

app = Celery(
    'when_trade',
    broker=broker_url,
    backend=result_backend,
    include=['core.tasks']  # 包含任务模块
)

# 配置
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # 任务结果过期时间
    result_expires=3600,
    # 任务软时间限制
    task_soft_time_limit=600,
    # 任务硬时间限制
    task_time_limit=1200,
    # Worker配置
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Beat配置（定时任务）
    beat_schedule={
        # 示例：每5分钟执行一次
        'check-system-health': {
            'task': 'core.tasks.check_system_health',
            'schedule': 300.0,  # 5分钟
        },
        # 示例：每天凌晨2点执行
        'cleanup-old-data': {
            'task': 'core.tasks.cleanup_old_data',
            'schedule': crontab(hour=2, minute=0),
        },
    }
)

if __name__ == '__main__':
    app.start()