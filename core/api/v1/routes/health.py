"""
健康检查端点
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import redis.asyncio as redis
from datetime import datetime

from core.database.session import get_db
from core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/health",
    tags=["health"]
)


@router.get("/", response_model=Dict[str, Any])
async def health_check():
    """
    基础健康检查
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.app_version,
        "environment": "development"
    }


@router.get("/ready", response_model=Dict[str, Any])
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    就绪检查 - 检查所有依赖服务
    """
    checks = {
        "database": False,
        "redis": False,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    # 检查数据库连接
    try:
        await db.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        
    # 检查Redis连接
    try:
        redis_client = await redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        await redis_client.close()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        
    # 判断整体状态
    all_healthy = all([
        checks["database"],
        checks["redis"]
    ])
    
    return {
        "status": "ready" if all_healthy else "not_ready",
        "checks": checks
    }


@router.get("/live", response_model=Dict[str, str])
async def liveness_check():
    """
    存活检查
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }