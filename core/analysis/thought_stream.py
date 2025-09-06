"""
思考流性能优化器
处理大量思考流数据的批处理、压缩和缓存
"""

import asyncio
import gzip
import json
import time
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
from datetime import datetime, timedelta
import logging

from core.agents.base import AgentThought, ThoughtType
from core.cache.manager import cache_manager

logger = logging.getLogger(__name__)


class ThoughtBatchProcessor:
    """思考流批处理器"""
    
    def __init__(
        self,
        batch_size: int = 50,
        batch_interval: float = 0.1,  # 100ms
        max_queue_size: int = 10000
    ):
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        self.max_queue_size = max_queue_size
        
        # 批处理队列：analysis_id -> thoughts
        self._queues: Dict[str, List[AgentThought]] = defaultdict(list)
        self._last_flush: Dict[str, float] = defaultdict(float)
        
        # 运行状态
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        
        # 统计信息
        self.stats = {
            "total_thoughts": 0,
            "batches_sent": 0,
            "thoughts_dropped": 0,
            "compression_ratio": 0.0
        }
    
    async def start(self):
        """启动批处理器"""
        if self._running:
            return
            
        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())
        logger.info("思考流批处理器已启动")
    
    async def stop(self):
        """停止批处理器"""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # 刷新所有剩余数据
        await self._flush_all()
        logger.info(f"思考流批处理器已停止，统计：{self.stats}")
    
    async def add_thought(self, analysis_id: str, thought: AgentThought):
        """添加思考到批处理队列"""
        queue = self._queues[analysis_id]
        
        # 检查队列大小
        if len(queue) >= self.max_queue_size:
            self.stats["thoughts_dropped"] += 1
            logger.warning(f"分析 {analysis_id} 的思考队列已满，丢弃最旧的思考")
            queue.pop(0)
        
        queue.append(thought)
        self.stats["total_thoughts"] += 1
        
        # 如果达到批大小，立即刷新
        if len(queue) >= self.batch_size:
            await self._flush_analysis(analysis_id)
    
    async def _flush_loop(self):
        """定期刷新批处理队列"""
        while self._running:
            try:
                await asyncio.sleep(self.batch_interval)
                
                # 检查需要刷新的分析
                current_time = time.time()
                to_flush = []
                
                for analysis_id, last_flush in self._last_flush.items():
                    if current_time - last_flush >= self.batch_interval:
                        if self._queues[analysis_id]:
                            to_flush.append(analysis_id)
                
                # 并发刷新
                if to_flush:
                    await asyncio.gather(
                        *[self._flush_analysis(aid) for aid in to_flush],
                        return_exceptions=True
                    )
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"批处理循环错误: {e}")
    
    async def _flush_analysis(self, analysis_id: str):
        """刷新特定分析的思考队列"""
        thoughts = self._queues[analysis_id]
        if not thoughts:
            return
        
        # 取出要发送的批次
        batch = thoughts[:self.batch_size]
        self._queues[analysis_id] = thoughts[self.batch_size:]
        self._last_flush[analysis_id] = time.time()
        
        # 准备批处理消息
        batch_data = {
            "type": "thought_batch",
            "analysis_id": analysis_id,
            "thoughts": [t.to_dict() for t in batch],
            "count": len(batch),
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 压缩数据
        compressed_data = await self._compress_data(batch_data)
        
        # 发送到WebSocket（延迟导入以避免循环导入）
        from core.websocket.manager import manager as websocket_manager
        await websocket_manager.broadcast_to_analysis(
            analysis_id=analysis_id,
            message=compressed_data
        )
        
        self.stats["batches_sent"] += 1
        
        # 缓存批次数据（用于回放）
        await self._cache_batch(analysis_id, batch)
    
    async def _flush_all(self):
        """刷新所有队列"""
        analysis_ids = list(self._queues.keys())
        await asyncio.gather(
            *[self._flush_analysis(aid) for aid in analysis_ids],
            return_exceptions=True
        )
    
    async def _compress_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """压缩数据"""
        original_json = json.dumps(data)
        original_size = len(original_json.encode())
        
        # 使用gzip压缩
        compressed = gzip.compress(original_json.encode())
        compressed_size = len(compressed)
        
        # 计算压缩率
        compression_ratio = 1 - (compressed_size / original_size)
        self.stats["compression_ratio"] = (
            self.stats["compression_ratio"] * 0.9 + compression_ratio * 0.1
        )
        
        # 如果压缩效果好，返回压缩数据
        if compression_ratio > 0.2:  # 至少20%的压缩率
            return {
                "type": "thought_batch_compressed",
                "data": compressed.hex(),  # 转为十六进制字符串
                "encoding": "gzip",
                "original_size": original_size,
                "compressed_size": compressed_size
            }
        
        # 否则返回原始数据
        return data
    
    async def _cache_batch(self, analysis_id: str, thoughts: List[AgentThought]):
        """缓存思考批次"""
        cache_key = f"thought_batch:{analysis_id}:{int(time.time())}"
        cache_data = {
            "thoughts": [t.to_dict() for t in thoughts],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # 缓存1小时
        await cache_manager.set(cache_key, cache_data, ttl=3600)


class ThoughtStreamOptimizer:
    """思考流优化器主类"""
    
    def __init__(self):
        self.batch_processor = ThoughtBatchProcessor()
        self.thought_cache = ThoughtCache()
        self.stream_aggregator = StreamAggregator()
        
        # WebSocket连接管理
        self._connections: Dict[str, Set[str]] = defaultdict(set)
        self._connection_stats: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self):
        """初始化优化器"""
        await self.batch_processor.start()
        logger.info("思考流优化器已初始化")
    
    async def shutdown(self):
        """关闭优化器"""
        await self.batch_processor.stop()
        logger.info("思考流优化器已关闭")
    
    async def process_thought(
        self,
        analysis_id: str,
        agent_id: str,
        thought: AgentThought
    ):
        """处理单个思考"""
        # 1. 聚合相似思考
        if self.stream_aggregator.should_aggregate(thought):
            aggregated = await self.stream_aggregator.aggregate(
                analysis_id, agent_id, thought
            )
            if not aggregated:
                return  # 被聚合了，不需要单独发送
            thought = aggregated
        
        # 2. 检查缓存
        if await self.thought_cache.is_duplicate(analysis_id, thought):
            return  # 重复思考，跳过
        
        # 3. 添加到批处理队列
        await self.batch_processor.add_thought(analysis_id, thought)
        
        # 4. 更新缓存
        await self.thought_cache.add(analysis_id, thought)
    
    def register_connection(self, analysis_id: str, connection_id: str):
        """注册WebSocket连接"""
        self._connections[analysis_id].add(connection_id)
        self._connection_stats[connection_id] = {
            "connected_at": datetime.utcnow(),
            "thoughts_sent": 0,
            "bytes_sent": 0
        }
    
    def unregister_connection(self, analysis_id: str, connection_id: str):
        """注销WebSocket连接"""
        self._connections[analysis_id].discard(connection_id)
        if connection_id in self._connection_stats:
            del self._connection_stats[connection_id]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取优化器统计信息"""
        return {
            "batch_processor": self.batch_processor.stats,
            "active_analyses": len(self._connections),
            "total_connections": sum(len(conns) for conns in self._connections.values()),
            "cache_stats": self.thought_cache.get_stats(),
            "aggregator_stats": self.stream_aggregator.get_stats()
        }


class ThoughtCache:
    """思考缓存管理"""
    
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0
        }
    
    async def is_duplicate(self, analysis_id: str, thought: AgentThought) -> bool:
        """检查是否为重复思考"""
        cache_key = self._get_cache_key(analysis_id, thought)
        
        # 清理过期项
        self._cleanup_expired()
        
        if cache_key in self._cache:
            self.stats["hits"] += 1
            self._access_times[cache_key] = time.time()
            return True
        
        self.stats["misses"] += 1
        return False
    
    async def add(self, analysis_id: str, thought: AgentThought):
        """添加思考到缓存"""
        cache_key = self._get_cache_key(analysis_id, thought)
        
        # 检查缓存大小
        if len(self._cache) >= self.max_size:
            self._evict_lru()
        
        self._cache[cache_key] = {
            "thought": thought.to_dict(),
            "added_at": time.time()
        }
        self._access_times[cache_key] = time.time()
    
    def _get_cache_key(self, analysis_id: str, thought: AgentThought) -> str:
        """生成缓存键"""
        # 基于内容生成键，避免完全相同的思考
        content_hash = hash(f"{thought.agent_id}:{thought.thought_type}:{thought.content[:100]}")
        return f"{analysis_id}:{content_hash}"
    
    def _cleanup_expired(self):
        """清理过期缓存项"""
        current_time = time.time()
        expired_keys = []
        
        for key, data in self._cache.items():
            if current_time - data["added_at"] > self.ttl_seconds:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
            del self._access_times[key]
            self.stats["evictions"] += 1
    
    def _evict_lru(self):
        """LRU驱逐"""
        if not self._access_times:
            return
        
        # 找到最久未访问的项
        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        
        del self._cache[lru_key]
        del self._access_times[lru_key]
        self.stats["evictions"] += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        hit_rate = self.stats["hits"] / max(1, self.stats["hits"] + self.stats["misses"])
        return {
            **self.stats,
            "size": len(self._cache),
            "hit_rate": hit_rate
        }


class StreamAggregator:
    """思考流聚合器"""
    
    def __init__(self, window_size: float = 1.0):
        self.window_size = window_size  # 聚合窗口（秒）
        self._windows: Dict[str, List[AgentThought]] = defaultdict(list)
        self._window_starts: Dict[str, float] = {}
        self.stats = {
            "aggregated_count": 0,
            "total_processed": 0
        }
    
    def should_aggregate(self, thought: AgentThought) -> bool:
        """判断是否应该聚合"""
        # 只聚合某些类型的思考
        aggregatable_types = {ThoughtType.OBSERVATION, ThoughtType.REASONING}
        return thought.thought_type in aggregatable_types
    
    async def aggregate(
        self,
        analysis_id: str,
        agent_id: str,
        thought: AgentThought
    ) -> Optional[AgentThought]:
        """聚合思考"""
        window_key = f"{analysis_id}:{agent_id}"
        current_time = time.time()
        
        # 检查窗口是否过期
        if window_key in self._window_starts:
            if current_time - self._window_starts[window_key] > self.window_size:
                # 窗口过期，返回聚合结果
                aggregated = self._create_aggregated_thought(
                    self._windows[window_key], agent_id
                )
                
                # 重置窗口
                self._windows[window_key] = [thought]
                self._window_starts[window_key] = current_time
                
                self.stats["aggregated_count"] += 1
                return aggregated
        else:
            self._window_starts[window_key] = current_time
        
        # 添加到窗口
        self._windows[window_key].append(thought)
        self.stats["total_processed"] += 1
        
        # 如果窗口内思考太多，立即聚合
        if len(self._windows[window_key]) >= 10:
            aggregated = self._create_aggregated_thought(
                self._windows[window_key], agent_id
            )
            self._windows[window_key] = []
            self.stats["aggregated_count"] += 1
            return aggregated
        
        return None  # 暂不发送，等待更多思考
    
    def _create_aggregated_thought(
        self,
        thoughts: List[AgentThought],
        agent_id: str
    ) -> AgentThought:
        """创建聚合思考"""
        if len(thoughts) == 1:
            return thoughts[0]
        
        # 按类型分组
        by_type = defaultdict(list)
        for t in thoughts:
            by_type[t.thought_type].append(t)
        
        # 创建聚合内容
        content_parts = []
        for thought_type, type_thoughts in by_type.items():
            if len(type_thoughts) == 1:
                content_parts.append(type_thoughts[0].content)
            else:
                content_parts.append(
                    f"[{thought_type.value} x{len(type_thoughts)}] " +
                    " | ".join(t.content[:50] + "..." for t in type_thoughts[:3])
                )
        
        # 创建聚合思考
        return AgentThought(
            thought_type=thoughts[0].thought_type,  # 使用第一个思考的类型
            content="\n".join(content_parts),
            agent_id=agent_id,
            confidence=sum(t.confidence for t in thoughts) / len(thoughts),
            metadata={
                "aggregated": True,
                "count": len(thoughts),
                "types": list(by_type.keys())
            }
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """获取聚合统计"""
        return {
            **self.stats,
            "active_windows": len(self._windows),
            "aggregation_rate": self.stats["aggregated_count"] / max(1, self.stats["total_processed"])
        }


# 创建全局优化器实例
thought_stream_optimizer = ThoughtStreamOptimizer()