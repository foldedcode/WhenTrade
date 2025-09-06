"""
性能监控器 - 监控API性能、数据库查询、缓存命中率等
"""

import time
import logging
import asyncio

# 条件导入psutil
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from functools import wraps
from contextlib import asynccontextmanager
from collections import defaultdict, deque
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.cache.manager import cache_manager

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """性能指标收集器"""
    
    def __init__(self):
        self.request_metrics = defaultdict(list)  # API请求指标
        self.db_metrics = defaultdict(list)       # 数据库查询指标
        self.cache_metrics = defaultdict(int)     # 缓存指标
        self.system_metrics = deque(maxlen=1000)  # 系统指标
        self.slow_queries = deque(maxlen=100)     # 慢查询记录
        self.error_counts = defaultdict(int)      # 错误统计
        
        # 性能阈值配置
        self.thresholds = {
            "slow_request": 2.0,     # 慢请求阈值（秒）
            "slow_query": 1.0,       # 慢查询阈值（秒）
            "high_cpu": 80.0,        # CPU使用率阈值
            "high_memory": 80.0,     # 内存使用率阈值
            "cache_hit_rate": 80.0   # 缓存命中率阈值
        }
        
    def record_request(self, endpoint: str, method: str, duration: float, status_code: int):
        """记录API请求指标"""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "duration": duration,
            "status_code": status_code
        }
        
        self.request_metrics[f"{method} {endpoint}"].append(metric)
        
        # 记录慢请求
        if duration > self.thresholds["slow_request"]:
            logger.warning(f"慢请求: {method} {endpoint} - {duration:.3f}s")
            
        # 保持最新的1000条记录
        if len(self.request_metrics[f"{method} {endpoint}"]) > 1000:
            self.request_metrics[f"{method} {endpoint}"].pop(0)
            
    def record_db_query(self, query_type: str, duration: float, query: str = None):
        """记录数据库查询指标"""
        metric = {
            "timestamp": datetime.utcnow().isoformat(),
            "query_type": query_type,
            "duration": duration,
            "query": query[:200] if query else None  # 截断长查询
        }
        
        self.db_metrics[query_type].append(metric)
        
        # 记录慢查询
        if duration > self.thresholds["slow_query"]:
            self.slow_queries.append(metric)
            logger.warning(f"慢查询: {query_type} - {duration:.3f}s")
            
        # 保持最新的1000条记录
        if len(self.db_metrics[query_type]) > 1000:
            self.db_metrics[query_type].pop(0)
            
    def record_cache_hit(self, cache_type: str = "general"):
        """记录缓存命中"""
        self.cache_metrics[f"{cache_type}_hits"] += 1
        
    def record_cache_miss(self, cache_type: str = "general"):
        """记录缓存未命中"""
        self.cache_metrics[f"{cache_type}_misses"] += 1
        
    def record_system_metrics(self):
        """记录系统指标"""
        if not PSUTIL_AVAILABLE:
            # 如果psutil不可用，记录基础系统信息
            metric = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_used": 0,
                "memory_total": 0,
                "disk_percent": 0.0,
                "disk_used": 0,
                "disk_total": 0,
                "note": "psutil_not_available"
            }
            self.system_metrics.append(metric)
            return
            
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            metric = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_used": memory.used,
                "memory_total": memory.total,
                "disk_percent": disk.percent,
                "disk_used": disk.used,
                "disk_total": disk.total
            }
            
            self.system_metrics.append(metric)
            
            # 检查阈值告警
            if cpu_percent > self.thresholds["high_cpu"]:
                logger.warning(f"CPU使用率过高: {cpu_percent:.1f}%")
                
            if memory.percent > self.thresholds["high_memory"]:
                logger.warning(f"内存使用率过高: {memory.percent:.1f}%")
                
        except Exception as e:
            logger.error(f"记录系统指标失败: {e}")
            
    def get_cache_hit_rate(self, cache_type: str = "general") -> float:
        """获取缓存命中率"""
        hits = self.cache_metrics.get(f"{cache_type}_hits", 0)
        misses = self.cache_metrics.get(f"{cache_type}_misses", 0)
        total = hits + misses
        
        if total == 0:
            return 0.0
            
        hit_rate = (hits / total) * 100
        
        if hit_rate < self.thresholds["cache_hit_rate"]:
            logger.warning(f"缓存命中率偏低 ({cache_type}): {hit_rate:.1f}%")
            
        return hit_rate
        
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        # API性能统计
        api_stats = {}
        for endpoint, metrics in self.request_metrics.items():
            recent_metrics = [
                m for m in metrics 
                if datetime.fromisoformat(m["timestamp"]) > last_hour
            ]
            
            if recent_metrics:
                durations = [m["duration"] for m in recent_metrics]
                api_stats[endpoint] = {
                    "count": len(recent_metrics),
                    "avg_duration": sum(durations) / len(durations),
                    "max_duration": max(durations),
                    "min_duration": min(durations),
                    "error_count": len([m for m in recent_metrics if m["status_code"] >= 400])
                }
                
        # 数据库性能统计
        db_stats = {}
        for query_type, metrics in self.db_metrics.items():
            recent_metrics = [
                m for m in metrics
                if datetime.fromisoformat(m["timestamp"]) > last_hour
            ]
            
            if recent_metrics:
                durations = [m["duration"] for m in recent_metrics]
                db_stats[query_type] = {
                    "count": len(recent_metrics),
                    "avg_duration": sum(durations) / len(durations),
                    "max_duration": max(durations)
                }
                
        # 系统性能统计
        recent_system = [
            m for m in self.system_metrics
            if datetime.fromisoformat(m["timestamp"]) > last_hour
        ]
        
        system_stats = {}
        if recent_system:
            cpu_values = [m["cpu_percent"] for m in recent_system]
            memory_values = [m["memory_percent"] for m in recent_system]
            
            system_stats = {
                "avg_cpu": sum(cpu_values) / len(cpu_values),
                "max_cpu": max(cpu_values),
                "avg_memory": sum(memory_values) / len(memory_values),
                "max_memory": max(memory_values)
            }
            
        return {
            "timestamp": now.isoformat(),
            "period": "last_hour",
            "api_performance": api_stats,
            "database_performance": db_stats,
            "system_performance": system_stats,
            "cache_hit_rates": {
                cache_type.replace("_hits", ""): self.get_cache_hit_rate(cache_type.replace("_hits", ""))
                for cache_type in self.cache_metrics.keys()
                if cache_type.endswith("_hits")
            },
            "slow_queries_count": len(self.slow_queries),
            "recent_slow_queries": list(self.slow_queries)[-10:]  # 最近10个慢查询
        }


# 全局性能指标收集器
performance_metrics = PerformanceMetrics()


def monitor_request(func: Callable):
    """API请求监控装饰器"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        status_code = 200
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status_code = getattr(e, 'status_code', 500)
            performance_metrics.error_counts[func.__name__] += 1
            raise
        finally:
            duration = time.time() - start_time
            endpoint = getattr(func, '__name__', 'unknown')
            method = 'POST'  # 大多数API是POST，可以从请求中获取实际方法
            
            performance_metrics.record_request(endpoint, method, duration, status_code)
            
    return wrapper


def monitor_db_query(query_type: str = "unknown"):
    """数据库查询监控装饰器"""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                performance_metrics.record_db_query(query_type, duration)
                
        return wrapper
    return decorator


@asynccontextmanager
async def monitor_operation(operation_name: str, operation_type: str = "general"):
    """通用操作监控上下文管理器"""
    start_time = time.time()
    
    try:
        yield
    finally:
        duration = time.time() - start_time
        
        if operation_type == "db":
            performance_metrics.record_db_query(operation_name, duration)
        else:
            # 记录到request_metrics中
            performance_metrics.record_request(operation_name, operation_type, duration, 200)


class DatabaseOptimizer:
    """数据库查询优化器"""
    
    def __init__(self):
        self.query_cache = {}
        self.optimization_suggestions = []
        
    async def analyze_slow_queries(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """分析慢查询"""
        try:
            # 获取PostgreSQL慢查询统计
            result = await db.execute(text("""
                SELECT query, calls, total_time, mean_time, max_time
                FROM pg_stat_statements 
                WHERE mean_time > 1000  -- 平均执行时间超过1秒
                ORDER BY mean_time DESC 
                LIMIT 20
            """))
            
            slow_queries = []
            for row in result:
                slow_queries.append({
                    "query": row.query[:200],  # 截断查询文本
                    "calls": row.calls,
                    "total_time": row.total_time,
                    "mean_time": row.mean_time,
                    "max_time": row.max_time
                })
                
            return slow_queries
            
        except Exception as e:
            logger.error(f"分析慢查询失败: {e}")
            return []
            
    async def get_table_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """获取表统计信息"""
        try:
            result = await db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    n_live_tup as row_count,
                    n_dead_tup as dead_rows,
                    last_vacuum,
                    last_autovacuum,
                    last_analyze,
                    last_autoanalyze
                FROM pg_stat_user_tables
                ORDER BY n_live_tup DESC
            """))
            
            tables = []
            for row in result:
                tables.append({
                    "schema": row.schemaname,
                    "table": row.tablename,
                    "row_count": row.row_count,
                    "dead_rows": row.dead_rows,
                    "last_vacuum": row.last_vacuum.isoformat() if row.last_vacuum else None,
                    "last_analyze": row.last_analyze.isoformat() if row.last_analyze else None,
                    "needs_vacuum": row.dead_rows > row.row_count * 0.1 if row.row_count > 0 else False
                })
                
            return {"tables": tables}
            
        except Exception as e:
            logger.error(f"获取表统计失败: {e}")
            return {"tables": []}
            
    async def get_index_usage(self, db: AsyncSession) -> List[Dict[str, Any]]:
        """获取索引使用情况"""
        try:
            result = await db.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_tup_read,
                    idx_tup_fetch,
                    idx_scan
                FROM pg_stat_user_indexes
                WHERE idx_scan = 0  -- 未使用的索引
                ORDER BY schemaname, tablename
            """))
            
            unused_indexes = []
            for row in result:
                unused_indexes.append({
                    "schema": row.schemaname,
                    "table": row.tablename,
                    "index": row.indexname,
                    "scans": row.idx_scan
                })
                
            return unused_indexes
            
        except Exception as e:
            logger.error(f"获取索引使用情况失败: {e}")
            return []
            
    def suggest_optimizations(self, stats: Dict[str, Any]) -> List[str]:
        """提供优化建议"""
        suggestions = []
        
        # 检查需要VACUUM的表
        for table in stats.get("tables", []):
            if table.get("needs_vacuum"):
                suggestions.append(f"表 {table['table']} 需要VACUUM清理，死行比例过高")
                
        # 检查缓存命中率
        cache_hit_rate = performance_metrics.get_cache_hit_rate()
        if cache_hit_rate < 80:
            suggestions.append(f"缓存命中率偏低 ({cache_hit_rate:.1f}%)，考虑优化缓存策略")
            
        # 检查慢查询
        if len(performance_metrics.slow_queries) > 10:
            suggestions.append("慢查询数量较多，建议添加索引或优化查询")
            
        return suggestions


class PerformanceOptimizer:
    """性能优化器"""
    
    def __init__(self):
        self.db_optimizer = DatabaseOptimizer()
        
    async def run_performance_analysis(self, db: AsyncSession) -> Dict[str, Any]:
        """运行完整的性能分析"""
        analysis_result = {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics_summary": performance_metrics.get_performance_summary(),
            "database_analysis": {},
            "optimization_suggestions": []
        }
        
        try:
            # 数据库分析
            slow_queries = await self.db_optimizer.analyze_slow_queries(db)
            table_stats = await self.db_optimizer.get_table_stats(db)
            unused_indexes = await self.db_optimizer.get_index_usage(db)
            
            analysis_result["database_analysis"] = {
                "slow_queries": slow_queries,
                "table_statistics": table_stats,
                "unused_indexes": unused_indexes
            }
            
            # 生成优化建议
            suggestions = self.db_optimizer.suggest_optimizations(table_stats)
            
            # 添加基于性能指标的建议
            summary = analysis_result["metrics_summary"]
            
            # API性能建议
            for endpoint, stats in summary.get("api_performance", {}).items():
                if stats["avg_duration"] > 2.0:
                    suggestions.append(f"API端点 {endpoint} 响应时间偏慢 ({stats['avg_duration']:.2f}s)")
                    
            # 系统资源建议
            system_perf = summary.get("system_performance", {})
            if system_perf.get("avg_cpu", 0) > 70:
                suggestions.append(f"CPU使用率偏高 ({system_perf['avg_cpu']:.1f}%)")
            if system_perf.get("avg_memory", 0) > 70:
                suggestions.append(f"内存使用率偏高 ({system_perf['avg_memory']:.1f}%)")
                
            analysis_result["optimization_suggestions"] = suggestions
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"性能分析失败: {e}")
            analysis_result["error"] = str(e)
            return analysis_result
            
    async def optimize_database_connections(self, db: AsyncSession):
        """优化数据库连接"""
        try:
            # 更新表统计信息
            await db.execute(text("ANALYZE;"))
            logger.info("数据库统计信息更新完成")
            
        except Exception as e:
            logger.error(f"优化数据库连接失败: {e}")
            
    async def warm_up_caches(self):
        """预热缓存"""
        try:
            from core.services.persistence_service import persistence_service
            
            # 这里可以添加预热逻辑
            # 例如：预加载热门用户、常用查询结果等
            
            logger.info("缓存预热完成")
            
        except Exception as e:
            logger.error(f"缓存预热失败: {e}")


# 全局性能优化器
performance_optimizer = PerformanceOptimizer()


async def start_performance_monitoring():
    """启动性能监控后台任务"""
    while True:
        try:
            # 每分钟记录一次系统指标
            performance_metrics.record_system_metrics()
            
            # 每小时生成一次性能报告
            if datetime.now().minute == 0:
                summary = performance_metrics.get_performance_summary()
                logger.info(f"性能摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")
                
            await asyncio.sleep(60)  # 等待1分钟
            
        except Exception as e:
            logger.error(f"性能监控异常: {e}")
            await asyncio.sleep(60)