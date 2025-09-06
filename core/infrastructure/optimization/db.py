"""
数据库优化器 - 优化数据库连接池、查询性能和资源使用
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable, AsyncGenerator
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from functools import wraps
import weakref

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, event
import sqlalchemy.pool

from core.config import settings
from core.infrastructure.monitoring import performance_metrics, monitor_db_query

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """连接池管理器"""
    
    def __init__(self):
        self.engines: Dict[str, Any] = {}
        self.session_factories: Dict[str, Any] = {}
        self.pool_stats: Dict[str, Dict] = {}
        self.connection_events: List[Dict] = []
        
        # 性能配置
        self.pool_configs = {
            "default": {
                "pool_size": 20,                    # 连接池大小
                "max_overflow": 30,                 # 最大溢出连接
                "pool_timeout": 30,                 # 连接超时
                "pool_recycle": 3600,               # 连接回收时间（1小时）
                "pool_pre_ping": True,              # 连接前ping
                "echo": False,                      # SQL回显
                "echo_pool": False                  # 连接池回显
            },
            "readonly": {
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 15,
                "pool_recycle": 7200,
                "pool_pre_ping": True,
                "echo": False,
                "echo_pool": False
            },
            "analytics": {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 60,
                "pool_recycle": 1800,
                "pool_pre_ping": True,
                "echo": False,
                "echo_pool": False
            }
        }
        
    def create_optimized_engine(self, pool_name: str = "default") -> Any:
        """创建优化的数据库引擎"""
        if pool_name in self.engines:
            return self.engines[pool_name]
            
        config = self.pool_configs.get(pool_name, self.pool_configs["default"])
        
        # 构建数据库URL
        database_url = (
            f"postgresql+asyncpg://{settings.database_user}:"
            f"{settings.database_password}@{settings.database_host}:"
            f"{settings.database_port}/{settings.database_name}"
        )
        
        # 创建引擎
        engine = create_async_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=config["pool_size"],
            max_overflow=config["max_overflow"],
            pool_timeout=config["pool_timeout"],
            pool_recycle=config["pool_recycle"],
            pool_pre_ping=config["pool_pre_ping"],
            echo=config["echo"],
            echo_pool=config["echo_pool"],
            # 异步优化参数
            connect_args={
                "server_settings": {
                    "jit": "off",                   # 关闭JIT以减少首次查询延迟
                    "application_name": "when_trade_api"
                }
            }
        )
        
        # 注册连接池事件监听
        self._register_pool_events(engine, pool_name)
        
        # 创建会话工厂
        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.engines[pool_name] = engine
        self.session_factories[pool_name] = session_factory
        self.pool_stats[pool_name] = {
            "created_connections": 0,
            "closed_connections": 0,
            "checked_out": 0,
            "checked_in": 0,
            "invalidated": 0
        }
        
        logger.info(f"创建优化数据库引擎: {pool_name}")
        return engine
        
    def _register_pool_events(self, engine: Any, pool_name: str):
        """注册连接池事件监听"""
        
        @event.listens_for(engine.sync_engine.pool, "connect")
        def receive_connect(dbapi_connection, connection_record):
            """连接创建事件"""
            self.pool_stats[pool_name]["created_connections"] += 1
            self.connection_events.append({
                "pool": pool_name,
                "event": "connect",
                "timestamp": datetime.utcnow().isoformat()
            })
            
        @event.listens_for(engine.sync_engine.pool, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """连接检出事件"""
            self.pool_stats[pool_name]["checked_out"] += 1
            
        @event.listens_for(engine.sync_engine.pool, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """连接检入事件"""
            self.pool_stats[pool_name]["checked_in"] += 1
            
        @event.listens_for(engine.sync_engine.pool, "invalidate")
        def receive_invalidate(dbapi_connection, connection_record, exception):
            """连接失效事件"""
            self.pool_stats[pool_name]["invalidated"] += 1
            logger.warning(f"数据库连接失效: {pool_name}, 异常: {exception}")
            
    def get_session_factory(self, pool_name: str = "default") -> Any:
        """获取会话工厂"""
        if pool_name not in self.session_factories:
            self.create_optimized_engine(pool_name)
        return self.session_factories[pool_name]
        
    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计"""
        stats = {}
        
        for pool_name, engine in self.engines.items():
            pool = engine.sync_engine.pool
            stats[pool_name] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalid(),
                **self.pool_stats[pool_name]
            }
            
        return stats
        
    async def health_check(self) -> Dict[str, Any]:
        """连接池健康检查"""
        health_status = {}
        
        for pool_name, engine in self.engines.items():
            try:
                async with engine.begin() as conn:
                    result = await conn.execute(text("SELECT 1"))
                    await result.fetchone()
                    
                health_status[pool_name] = {
                    "status": "healthy",
                    "last_check": datetime.utcnow().isoformat()
                }
            except Exception as e:
                health_status[pool_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "last_check": datetime.utcnow().isoformat()
                }
                logger.error(f"连接池健康检查失败: {pool_name}, 错误: {e}")
                
        return health_status
        
    async def close_all(self):
        """关闭所有引擎"""
        for pool_name, engine in self.engines.items():
            await engine.dispose()
            logger.info(f"已关闭数据库引擎: {pool_name}")
        
        self.engines.clear()
        self.session_factories.clear()


class QueryOptimizer:
    """查询优化器"""
    
    def __init__(self):
        self.query_cache: Dict[str, Dict] = {}
        self.slow_queries: List[Dict] = []
        self.query_stats: Dict[str, Dict] = {}
        
    def cache_query_result(
        self, 
        query_key: str, 
        result: Any, 
        ttl: int = 300
    ):
        """缓存查询结果"""
        self.query_cache[query_key] = {
            "result": result,
            "cached_at": time.time(),
            "ttl": ttl
        }
        
    def get_cached_result(self, query_key: str) -> Optional[Any]:
        """获取缓存的查询结果"""
        if query_key not in self.query_cache:
            return None
            
        cached = self.query_cache[query_key]
        
        # 检查TTL
        if time.time() - cached["cached_at"] > cached["ttl"]:
            del self.query_cache[query_key]
            return None
            
        return cached["result"]
        
    def record_query_stats(
        self, 
        query_type: str, 
        duration: float, 
        rows_affected: int = 0
    ):
        """记录查询统计"""
        if query_type not in self.query_stats:
            self.query_stats[query_type] = {
                "count": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0,
                "total_rows": 0
            }
            
        stats = self.query_stats[query_type]
        stats["count"] += 1
        stats["total_duration"] += duration
        stats["min_duration"] = min(stats["min_duration"], duration)
        stats["max_duration"] = max(stats["max_duration"], duration)
        stats["total_rows"] += rows_affected
        
        # 记录慢查询
        if duration > 1.0:  # 1秒阈值
            self.slow_queries.append({
                "query_type": query_type,
                "duration": duration,
                "rows_affected": rows_affected,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            # 保持最新100个慢查询
            if len(self.slow_queries) > 100:
                self.slow_queries.pop(0)
                
    def get_query_statistics(self) -> Dict[str, Any]:
        """获取查询统计信息"""
        summary = {}
        
        for query_type, stats in self.query_stats.items():
            if stats["count"] > 0:
                summary[query_type] = {
                    "count": stats["count"],
                    "avg_duration": stats["total_duration"] / stats["count"],
                    "min_duration": stats["min_duration"],
                    "max_duration": stats["max_duration"],
                    "total_rows": stats["total_rows"],
                    "avg_rows": stats["total_rows"] / stats["count"] if stats["count"] > 0 else 0
                }
                
        return {
            "query_statistics": summary,
            "slow_queries": self.slow_queries[-10:],  # 最近10个慢查询
            "cache_size": len(self.query_cache)
        }


# 数据库会话装饰器
def optimized_db_session(pool_name: str = "default", cache_key: Optional[str] = None):
    """优化的数据库会话装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 检查缓存
            if cache_key:
                cached_result = query_optimizer.get_cached_result(cache_key)
                if cached_result is not None:
                    performance_metrics.record_cache_hit("database")
                    return cached_result
                else:
                    performance_metrics.record_cache_miss("database")
                    
            # 执行查询
            start_time = time.time()
            session_factory = connection_pool.get_session_factory(pool_name)
            
            async with session_factory() as session:
                try:
                    result = await func(session, *args, **kwargs)
                    
                    # 缓存结果
                    if cache_key:
                        query_optimizer.cache_query_result(cache_key, result)
                        
                    return result
                    
                except Exception as e:
                    await session.rollback()
                    raise
                finally:
                    duration = time.time() - start_time
                    query_optimizer.record_query_stats(func.__name__, duration)
                    performance_metrics.record_db_query(func.__name__, duration)
                    
        return wrapper
    return decorator


@asynccontextmanager
async def optimized_session(pool_name: str = "default") -> AsyncGenerator[AsyncSession, None]:
    """优化的数据库会话上下文管理器"""
    start_time = time.time()
    session_factory = connection_pool.get_session_factory(pool_name)
    
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            duration = time.time() - start_time
            query_optimizer.record_query_stats("session", duration)


class TransactionManager:
    """事务管理器"""
    
    def __init__(self):
        self.active_transactions: Dict[str, Dict] = {}
        self.transaction_stats: Dict[str, int] = {
            "commits": 0,
            "rollbacks": 0,
            "deadlocks": 0
        }
        
    @asynccontextmanager
    async def managed_transaction(
        self, 
        session: AsyncSession,
        isolation_level: Optional[str] = None
    ):
        """托管事务上下文"""
        transaction_id = f"tx_{id(session)}_{time.time()}"
        
        self.active_transactions[transaction_id] = {
            "started_at": time.time(),
            "isolation_level": isolation_level
        }
        
        try:
            if isolation_level:
                await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
                
            yield session
            await session.commit()
            self.transaction_stats["commits"] += 1
            
        except Exception as e:
            await session.rollback()
            self.transaction_stats["rollbacks"] += 1
            
            if "deadlock" in str(e).lower():
                self.transaction_stats["deadlocks"] += 1
                logger.warning(f"检测到数据库死锁: {e}")
                
            raise
        finally:
            self.active_transactions.pop(transaction_id, None)
            
    def get_transaction_stats(self) -> Dict[str, Any]:
        """获取事务统计"""
        return {
            "active_transactions": len(self.active_transactions),
            "statistics": self.transaction_stats,
            "long_running_transactions": [
                {
                    "id": tx_id,
                    "duration": time.time() - tx_info["started_at"]
                }
                for tx_id, tx_info in self.active_transactions.items()
                if time.time() - tx_info["started_at"] > 30  # 超过30秒的事务
            ]
        }


class DatabaseOptimizer:
    """数据库优化器主类"""
    
    def __init__(self):
        self.connection_pool = ConnectionPoolManager()
        self.query_optimizer = QueryOptimizer()
        self.transaction_manager = TransactionManager()
        self._monitoring_task: Optional[asyncio.Task] = None
        
    async def initialize(self):
        """初始化优化器"""
        # 创建默认引擎
        self.connection_pool.create_optimized_engine("default")
        
        # 创建只读引擎
        self.connection_pool.create_optimized_engine("readonly")
        
        # 创建分析引擎
        self.connection_pool.create_optimized_engine("analytics")
        
        # 启动监控任务
        self._monitoring_task = asyncio.create_task(self._monitor_database_performance())
        
        logger.info("数据库优化器初始化完成")
        
    async def _monitor_database_performance(self):
        """监控数据库性能"""
        while True:
            try:
                # 获取连接池统计
                pool_stats = self.connection_pool.get_pool_stats()
                
                # 检查连接池健康状况
                for pool_name, stats in pool_stats.items():
                    # 检查连接池使用率
                    if stats["checked_out"] > stats["size"] * 0.8:
                        logger.warning(f"连接池使用率高: {pool_name}, {stats['checked_out']}/{stats['size']}")
                        
                    # 检查溢出连接
                    if stats["overflow"] > 0:
                        logger.info(f"连接池溢出: {pool_name}, 溢出连接: {stats['overflow']}")
                        
                # 检查慢查询
                query_stats = self.query_optimizer.get_query_statistics()
                if len(query_stats.get("slow_queries", [])) > 0:
                    logger.warning(f"发现慢查询: {len(query_stats['slow_queries'])}")
                    
                # 每5分钟输出统计信息
                if datetime.now().minute % 5 == 0 and datetime.now().second < 10:
                    logger.info(f"数据库性能统计: 连接池={pool_stats}, 查询={query_stats}")
                    
                await asyncio.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"数据库性能监控异常: {e}")
                await asyncio.sleep(60)
                
    def get_optimization_recommendations(self) -> List[str]:
        """获取优化建议"""
        recommendations = []
        
        # 连接池建议
        pool_stats = self.connection_pool.get_pool_stats()
        for pool_name, stats in pool_stats.items():
            if stats["checked_out"] / stats["size"] > 0.9:
                recommendations.append(f"考虑增加 {pool_name} 连接池大小")
                
            if stats["invalidated"] > 10:
                recommendations.append(f"{pool_name} 连接失效过多，检查网络稳定性")
                
        # 查询优化建议
        query_stats = self.query_optimizer.get_query_statistics()
        for query_type, stats in query_stats.get("query_statistics", {}).items():
            if stats["avg_duration"] > 2.0:
                recommendations.append(f"查询 {query_type} 平均耗时过长，考虑添加索引")
                
        # 事务建议
        tx_stats = self.transaction_manager.get_transaction_stats()
        if tx_stats["statistics"]["deadlocks"] > 5:
            recommendations.append("死锁频繁发生，优化事务顺序和持有时间")
            
        return recommendations
        
    async def perform_maintenance(self):
        """执行数据库维护"""
        try:
            async with optimized_session("default") as session:
                # 更新统计信息
                await session.execute(text("ANALYZE;"))
                logger.info("数据库统计信息更新完成")
                
                # 清理查询缓存
                self.query_optimizer.query_cache.clear()
                logger.info("查询缓存已清理")
                
        except Exception as e:
            logger.error(f"数据库维护失败: {e}")
            
    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息"""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "connection_pools": self.connection_pool.get_pool_stats(),
            "query_performance": self.query_optimizer.get_query_statistics(),
            "transactions": self.transaction_manager.get_transaction_stats(),
            "health_check": await self.connection_pool.health_check(),
            "optimization_recommendations": self.get_optimization_recommendations()
        }
        
    async def shutdown(self):
        """关闭优化器"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            
        await self.connection_pool.close_all()
        logger.info("数据库优化器已关闭")


# 全局实例
connection_pool = ConnectionPoolManager()
query_optimizer = QueryOptimizer()
transaction_manager = TransactionManager()
db_optimizer = DatabaseOptimizer()