"""
增强的缓存服务
提供数据预加载、预热、失效策略等高级功能
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import json

from core.cache.manager import cache_manager
# from core.adapter_registry import adapter_registry  # TODO: 需要修复缺失的依赖

logger = logging.getLogger(__name__)


class CacheService:
    """增强的缓存服务"""
    
    def __init__(self):
        self.preload_tasks: Dict[str, asyncio.Task] = {}
        self.cache_strategies: Dict[str, Dict[str, Any]] = {}
        self.warmup_config: Dict[str, List[str]] = {}
        self._init_default_strategies()
        
    def _init_default_strategies(self):
        """初始化默认缓存策略"""
        # 股票数据缓存策略
        self.cache_strategies["stock"] = {
            "ttl": 300,  # 5分钟
            "refresh_interval": 240,  # 4分钟刷新（提前1分钟）
            "priority": "high",
            "preload": True
        }
        
        # 加密货币缓存策略（更频繁更新）
        self.cache_strategies["crypto"] = {
            "ttl": 60,  # 1分钟
            "refresh_interval": 45,  # 45秒刷新
            "priority": "high",
            "preload": True
        }
        
        # 技术指标缓存策略
        self.cache_strategies["indicators"] = {
            "ttl": 600,  # 10分钟
            "refresh_interval": 540,  # 9分钟刷新
            "priority": "medium",
            "preload": False
        }
        
        # 基本面数据缓存策略（更长时间）
        self.cache_strategies["fundamentals"] = {
            "ttl": 3600,  # 1小时
            "refresh_interval": 3300,  # 55分钟刷新
            "priority": "low",
            "preload": False
        }
        
    async def configure_warmup(self, market: str, symbols: List[str]):
        """配置缓存预热"""
        self.warmup_config[market] = symbols
        logger.info(f"配置缓存预热 - 市场: {market}, 标的数量: {len(symbols)}")
        
    async def warmup_cache(self, market: Optional[str] = None):
        """执行缓存预热"""
        markets = [market] if market else list(self.warmup_config.keys())
        
        for mkt in markets:
            symbols = self.warmup_config.get(mkt, [])
            if not symbols:
                continue
                
            logger.info(f"开始预热缓存 - 市场: {mkt}, 标的: {symbols}")
            
            # 获取对应的适配器
            adapter = adapter_registry.get_adapter_by_market(mkt)
            if not adapter:
                logger.error(f"未找到市场 {mkt} 的适配器")
                continue
                
            # 并发预热多个标的
            tasks = []
            for symbol in symbols:
                task = self._warmup_symbol(adapter, symbol, mkt)
                tasks.append(task)
                
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            success_count = sum(1 for r in results if not isinstance(r, Exception))
            logger.info(f"缓存预热完成 - 市场: {mkt}, 成功: {success_count}/{len(symbols)}")
            
    async def _warmup_symbol(self, adapter, symbol: str, market: str):
        """预热单个标的"""
        try:
            # 根据市场类型设置参数
            params = self._get_warmup_params(market)
            
            # 获取数据（会自动缓存）
            data = await adapter.fetch_data(symbol, params)
            
            logger.debug(f"预热成功: {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"预热失败 {symbol}: {e}")
            return False
            
    def _get_warmup_params(self, market: str) -> Dict[str, Any]:
        """获取预热参数"""
        if market == "crypto":
            return {
                "interval": "1h",
                "limit": 24,  # 24小时数据
                "include_indicators": True
            }
        elif market == "stock_us":
            return {
                "period": "1d",
                "interval": "5m",
                "include_indicators": True
            }
        else:
            return {
                "include_indicators": True
            }
            
    async def start_preload_service(self):
        """启动预加载服务"""
        logger.info("启动缓存预加载服务")
        
        # 为每个市场启动预加载任务
        for market, config in self.warmup_config.items():
            if config:  # 如果有配置的标的
                task = asyncio.create_task(self._preload_loop(market))
                self.preload_tasks[market] = task
                
    async def stop_preload_service(self):
        """停止预加载服务"""
        logger.info("停止缓存预加载服务")
        
        # 取消所有预加载任务
        for market, task in self.preload_tasks.items():
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.debug(f"预加载任务已取消: {market}")
                    
        self.preload_tasks.clear()
        
    async def _preload_loop(self, market: str):
        """预加载循环"""
        strategy = self.cache_strategies.get(
            "crypto" if market == "crypto" else "stock"
        )
        refresh_interval = strategy["refresh_interval"]
        
        while True:
            try:
                # 执行预加载
                await self._preload_market_data(market)
                
                # 等待下次刷新
                await asyncio.sleep(refresh_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"预加载循环错误 {market}: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟重试
                
    async def _preload_market_data(self, market: str):
        """预加载市场数据"""
        symbols = self.warmup_config.get(market, [])
        if not symbols:
            return
            
        logger.debug(f"预加载市场数据 - {market}: {len(symbols)} 个标的")
        
        adapter = adapter_registry.get_adapter_by_market(market)
        if not adapter:
            return
            
        # 并发加载
        tasks = []
        for symbol in symbols:
            task = self._refresh_symbol_cache(adapter, symbol, market)
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)
        
    async def _refresh_symbol_cache(self, adapter, symbol: str, market: str):
        """刷新单个标的缓存"""
        try:
            # 构建缓存键
            cache_key = self._build_cache_key(market, symbol)
            
            # 检查是否需要刷新
            ttl = await cache_manager.get_ttl(cache_key)
            strategy = self.cache_strategies.get(
                "crypto" if market == "crypto" else "stock"
            )
            
            # 如果TTL还很长，跳过刷新
            if ttl and ttl > strategy["ttl"] - strategy["refresh_interval"]:
                return
                
            # 获取新数据
            params = self._get_warmup_params(market)
            data = await adapter.fetch_data(symbol, params)
            
            # 更新缓存
            await cache_manager.set(
                cache_key,
                data,
                ttl=strategy["ttl"],
                serialize_method="json"
            )
            
            logger.debug(f"刷新缓存成功: {symbol}")
            
        except Exception as e:
            logger.error(f"刷新缓存失败 {symbol}: {e}")
            
    def _build_cache_key(self, market: str, symbol: str) -> str:
        """构建缓存键"""
        adapter_map = {
            "crypto": "coingecko"
        }
        adapter_id = adapter_map.get(market, market)
        return f"{adapter_id}:{symbol}:1d"  # 默认使用1天的key
        
    async def invalidate_cache(self, pattern: str):
        """失效缓存（按模式）"""
        count = await cache_manager.clear_pattern(pattern)
        logger.info(f"失效缓存 - 模式: {pattern}, 清理数量: {count}")
        return count
        
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        stats = await cache_manager.get_cache_stats()
        
        # 添加额外统计
        total_keys = 0
        for market in self.warmup_config:
            pattern = f"*{market}*"
            # 这里简化处理，实际可以实现keys count
            total_keys += len(self.warmup_config.get(market, []))
            
        stats["managed_keys"] = total_keys
        stats["preload_tasks"] = len(self.preload_tasks)
        stats["active_markets"] = list(self.warmup_config.keys())
        
        # 计算命中率
        hits = stats.get("keyspace_hits", 0)
        misses = stats.get("keyspace_misses", 0)
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        stats["hit_rate"] = round(hit_rate, 2)
        
        return stats
        
    async def optimize_cache(self):
        """优化缓存（清理过期数据，调整策略）"""
        logger.info("开始缓存优化")
        
        # 获取当前统计
        stats = await self.get_cache_statistics()
        hit_rate = stats.get("hit_rate", 0)
        
        # 根据命中率调整策略
        if hit_rate < 70:
            logger.warning(f"缓存命中率较低: {hit_rate}%，考虑增加预热标的")
            # 可以实现自动调整逻辑
            
        # 清理过期数据
        # Redis会自动处理过期，这里可以实现额外的清理逻辑
        
        logger.info(f"缓存优化完成 - 命中率: {hit_rate}%")
        
    def register_invalidation_handler(self, event: str, handler: Callable):
        """注册缓存失效处理器"""
        # 可以实现事件驱动的缓存失效
        pass


# 全局缓存服务实例
cache_service = CacheService()