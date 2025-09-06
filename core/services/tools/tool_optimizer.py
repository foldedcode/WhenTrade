"""
工具调用优化器

优化Agent工具调用，减少API并发压力，提高成功率
"""
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging
from concurrent.futures import ThreadPoolExecutor
import threading

logger = logging.getLogger(__name__)


class ToolPriority(Enum):
    """工具调用优先级"""
    HIGH = 1      # 关键数据（价格、市值等）
    MEDIUM = 2    # 技术指标
    LOW = 3       # 新闻、情绪等


@dataclass
class ToolCall:
    """工具调用请求"""
    id: str
    tool_name: str
    priority: ToolPriority
    args: tuple
    kwargs: dict
    agent_id: str
    created_at: float = field(default_factory=time.time)
    
    def __lt__(self, other):
        """优先级比较（数值小的优先级高）"""
        if self.priority.value != other.priority.value:
            return self.priority.value < other.priority.value
        return self.created_at < other.created_at


class ToolCallOptimizer:
    """工具调用优化器"""
    
    def __init__(self, max_concurrent_calls: int = 5, max_api_calls_per_minute: int = 30):
        """
        初始化优化器
        
        Args:
            max_concurrent_calls: 最大并发调用数
            max_api_calls_per_minute: 每分钟最大API调用数
        """
        self.max_concurrent_calls = max_concurrent_calls
        self.max_api_calls_per_minute = max_api_calls_per_minute
        
        # 调用队列（按优先级排序）
        self.call_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # 活动调用追踪
        self.active_calls: Dict[str, ToolCall] = {}
        
        # API调用历史（用于速率控制）
        self.api_call_history: List[float] = []
        
        # 执行器
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_calls)
        
        # 统计信息
        self.stats = {
            'total_calls': 0,
            'completed_calls': 0,
            'failed_calls': 0,
            'queued_calls': 0,
            'cached_calls': 0
        }
        
        # 启动工作线程
        self._running = True
        self._worker_task = None
        
        logger.info(f"🔧 工具调用优化器初始化完成 - 最大并发: {max_concurrent_calls}")
    
    async def start(self):
        """启动优化器"""
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("🚀 工具调用优化器已启动")
    
    async def stop(self):
        """停止优化器"""
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        self.executor.shutdown(wait=True)
        logger.info("⏹️ 工具调用优化器已停止")
    
    def submit_call(
        self,
        tool_name: str,
        tool_func,
        args: tuple = (),
        kwargs: dict = None,
        agent_id: str = "unknown",
        priority: ToolPriority = ToolPriority.MEDIUM
    ) -> asyncio.Future:
        """
        提交工具调用请求
        
        Args:
            tool_name: 工具名称
            tool_func: 工具函数
            args: 位置参数
            kwargs: 关键字参数
            agent_id: 调用方Agent ID
            priority: 调用优先级
            
        Returns:
            异步Future对象
        """
        kwargs = kwargs or {}
        call_id = f"{agent_id}_{tool_name}_{time.time()}"
        
        # 创建调用请求
        call = ToolCall(
            id=call_id,
            tool_name=tool_name,
            priority=priority,
            args=args,
            kwargs=kwargs,
            agent_id=agent_id
        )
        
        # 创建Future用于返回结果
        future = asyncio.Future()
        
        # 将调用请求和Future存储
        self.call_queue.put_nowait((priority.value, call, tool_func, future))
        self.stats['total_calls'] += 1
        self.stats['queued_calls'] += 1
        
        logger.debug(f"📝 工具调用已提交: {tool_name} (Agent: {agent_id}, Priority: {priority.name})")
        return future
    
    async def _worker_loop(self):
        """工作循环"""
        while self._running:
            try:
                # 控制并发数量
                if len(self.active_calls) >= self.max_concurrent_calls:
                    await asyncio.sleep(0.1)
                    continue
                
                # 控制API调用频率
                if not self._can_make_api_call():
                    await asyncio.sleep(1.0)
                    continue
                
                # 从队列获取调用请求
                try:
                    priority, call, tool_func, future = await asyncio.wait_for(
                        self.call_queue.get(), timeout=0.1
                    )
                    self.stats['queued_calls'] -= 1
                except asyncio.TimeoutError:
                    continue
                
                # 执行调用
                await self._execute_call(call, tool_func, future)
                
            except asyncio.CancelledError:
                logger.info("🛑 工具调用优化器工作循环已取消")
                break
            except Exception as e:
                logger.error(f"❌ 工具调用优化器工作循环异常: {e}")
                await asyncio.sleep(0.1)
    
    def _can_make_api_call(self) -> bool:
        """检查是否可以进行API调用"""
        now = time.time()
        # 清理1分钟前的记录
        self.api_call_history = [
            call_time for call_time in self.api_call_history
            if now - call_time < 60
        ]
        
        # 检查是否超出频率限制
        return len(self.api_call_history) < self.max_api_calls_per_minute
    
    async def _execute_call(self, call: ToolCall, tool_func, future: asyncio.Future):
        """执行单个工具调用"""
        self.active_calls[call.id] = call
        
        try:
            logger.debug(f"🔄 开始执行工具调用: {call.tool_name} (Agent: {call.agent_id})")
            
            # 记录API调用时间
            self.api_call_history.append(time.time())
            
            # 在线程池中执行同步函数
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(*call.args, **call.kwargs)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    self.executor, 
                    lambda: tool_func(*call.args, **call.kwargs)
                )
            
            # 设置结果
            if not future.cancelled():
                future.set_result(result)
            
            self.stats['completed_calls'] += 1
            logger.debug(f"✅ 工具调用完成: {call.tool_name} (Agent: {call.agent_id})")
            
        except Exception as e:
            logger.error(f"❌ 工具调用失败: {call.tool_name} (Agent: {call.agent_id}) - {e}")
            
            # 设置异常
            if not future.cancelled():
                future.set_exception(e)
            
            self.stats['failed_calls'] += 1
            
        finally:
            # 清理活动调用
            if call.id in self.active_calls:
                del self.active_calls[call.id]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self.stats,
            'active_calls': len(self.active_calls),
            'queue_size': self.call_queue.qsize(),
            'api_calls_last_minute': len(self.api_call_history),
            'max_concurrent_calls': self.max_concurrent_calls,
            'max_api_calls_per_minute': self.max_api_calls_per_minute
        }
    
    def clear_stats(self):
        """清空统计信息"""
        self.stats = {
            'total_calls': 0,
            'completed_calls': 0,
            'failed_calls': 0,
            'queued_calls': self.call_queue.qsize(),
            'cached_calls': 0
        }


# 全局优化器实例
_tool_optimizer = None


async def get_optimizer() -> ToolCallOptimizer:
    """获取全局工具调用优化器"""
    global _tool_optimizer
    if _tool_optimizer is None:
        _tool_optimizer = ToolCallOptimizer(max_concurrent_calls=5, max_api_calls_per_minute=30)
        await _tool_optimizer.start()
    return _tool_optimizer


async def optimize_tool_call(
    tool_name: str,
    tool_func,
    args: tuple = (),
    kwargs: dict = None,
    agent_id: str = "unknown",
    priority: ToolPriority = ToolPriority.MEDIUM
) -> Any:
    """
    优化的工具调用接口
    
    Args:
        tool_name: 工具名称
        tool_func: 工具函数
        args: 位置参数
        kwargs: 关键字参数
        agent_id: 调用方Agent ID
        priority: 调用优先级
        
    Returns:
        工具调用结果
    """
    optimizer = await get_optimizer()
    future = optimizer.submit_call(tool_name, tool_func, args, kwargs, agent_id, priority)
    return await future


def get_tool_priority(tool_name: str) -> ToolPriority:
    """
    根据工具名称获取优先级
    
    Args:
        tool_name: 工具名称
        
    Returns:
        工具调用优先级
    """
    # 高优先级工具（关键市场数据）
    high_priority_tools = {
        'get_crypto_price_data',
        'get_coin_market_data', 
        'get_market_metrics'
    }
    
    # 中优先级工具（技术指标）
    medium_priority_tools = {
        'calculate_technical_indicators',
        'get_historical_prices'
    }
    
    # 低优先级工具（新闻、情绪等）
    low_priority_tools = {
        'get_crypto_news',
        'get_reddit_sentiment',
        'get_fear_greed_index',
        'get_trending_coins'
    }
    
    if tool_name in high_priority_tools:
        return ToolPriority.HIGH
    elif tool_name in medium_priority_tools:
        return ToolPriority.MEDIUM
    elif tool_name in low_priority_tools:
        return ToolPriority.LOW
    else:
        return ToolPriority.MEDIUM  # 默认中等优先级