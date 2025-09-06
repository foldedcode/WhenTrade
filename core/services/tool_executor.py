"""
优化的工具执行器服务
"""

import asyncio
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime, timedelta
import hashlib
import json
from collections import deque
from asyncio import Queue, QueueFull
import time

from core.cache.redis_client import redis_client
# TODO: Import from tools module when implemented
# from core.tools.legacy.registry import tool_registry
# from core.tools.legacy.base import ToolContext, ToolResult, ToolType

# Temporary type definitions
from typing import NamedTuple

class ToolResult(NamedTuple):
    success: bool
    data: Any
    error: Optional[str] = None

class ToolContext(dict):
    pass
import logging

logger = logging.getLogger(__name__)


class ExecutionCache:
    """执行结果缓存"""
    
    def __init__(self, ttl: int = 300):  # 默认5分钟缓存
        self.ttl = ttl
        
    def _get_cache_key(self, tool_name: str, context: ToolContext) -> str:
        """生成缓存键"""
        # 创建上下文的稳定哈希
        context_data = {
            "symbol": context.symbol,
            "market_type": context.market_type,
            "timeframe": context.timeframe,
            "parameters": context.parameters
        }
        context_hash = hashlib.md5(
            json.dumps(context_data, sort_keys=True).encode()
        ).hexdigest()
        
        return f"tool_exec:{tool_name}:{context_hash}"
        
    async def get(self, tool_name: str, context: ToolContext) -> Optional[ToolResult]:
        """从缓存获取结果"""
        key = self._get_cache_key(tool_name, context)
        
        try:
            cached_data = await redis_client.get(key)
            if cached_data:
                data = json.loads(cached_data)
                return ToolResult(**data)
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            
        return None
        
    async def set(self, tool_name: str, context: ToolContext, result: ToolResult) -> None:
        """设置缓存结果"""
        key = self._get_cache_key(tool_name, context)
        
        try:
            await redis_client.setex(
                key,
                self.ttl,
                json.dumps(result.dict(), default=str)
            )
        except Exception as e:
            logger.error(f"Cache set error: {e}")


class ExecutionPool:
    """执行池，管理并发执行"""
    
    def __init__(self, max_workers: int = 10, max_queue_size: int = 100):
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.queue: Queue[Tuple[str, ToolContext, asyncio.Future]] = Queue(maxsize=max_queue_size)
        self.workers: List[asyncio.Task] = []
        self.running = False
        self._start_time = None
        self._execution_count = 0
        self._error_count = 0
        
    async def start(self):
        """启动执行池"""
        if self.running:
            return
            
        self.running = True
        self._start_time = time.time()
        
        # 创建工作任务
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
            
        logger.info(f"ExecutionPool started with {self.max_workers} workers")
        
    async def stop(self):
        """停止执行池"""
        self.running = False
        
        # 等待队列处理完成
        await self.queue.join()
        
        # 取消所有工作任务
        for worker in self.workers:
            worker.cancel()
            
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info(f"ExecutionPool stopped. Executed: {self._execution_count}, Errors: {self._error_count}")
        
    async def execute(self, tool_name: str, context: ToolContext) -> ToolResult:
        """提交执行任务"""
        if not self.running:
            raise RuntimeError("ExecutionPool is not running")
            
        future = asyncio.get_event_loop().create_future()
        
        try:
            # 尝试立即放入队列
            self.queue.put_nowait((tool_name, context, future))
        except QueueFull:
            # 队列满，等待空间
            await self.queue.put((tool_name, context, future))
            
        return await future
        
    async def _worker(self, worker_id: str):
        """工作任务"""
        logger.debug(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # 获取任务
                tool_name, context, future = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )
                
                # 执行任务
                try:
                    # TODO: Use tool_registry when available
                    # result = await tool_registry.execute_tool(tool_name, context)
                    result = ToolResult(
                        success=True,
                        data={"result": f"Executed {tool_name}"},
                        error=None
                    )
                    future.set_result(result)
                    self._execution_count += 1
                except Exception as e:
                    future.set_exception(e)
                    self._error_count += 1
                    logger.error(f"Worker {worker_id} execution error: {e}")
                finally:
                    self.queue.task_done()
                    
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                
        logger.debug(f"Worker {worker_id} stopped")
        
    def get_stats(self) -> Dict[str, Any]:
        """获取执行池统计"""
        uptime = time.time() - self._start_time if self._start_time else 0
        
        return {
            "running": self.running,
            "workers": self.max_workers,
            "queue_size": self.queue.qsize(),
            "max_queue_size": self.max_queue_size,
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "uptime_seconds": uptime,
            "executions_per_second": self._execution_count / uptime if uptime > 0 else 0
        }


class BatchExecutor:
    """批量执行器，优化批量工具执行"""
    
    def __init__(self, batch_size: int = 50, batch_timeout: float = 0.1):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_executions: deque = deque()
        self.batch_task: Optional[asyncio.Task] = None
        
    async def start(self):
        """启动批量执行器"""
        if self.batch_task:
            return
            
        self.batch_task = asyncio.create_task(self._batch_processor())
        logger.info("BatchExecutor started")
        
    async def stop(self):
        """停止批量执行器"""
        if self.batch_task:
            self.batch_task.cancel()
            await asyncio.gather(self.batch_task, return_exceptions=True)
            self.batch_task = None
            
        logger.info("BatchExecutor stopped")
        
    async def execute(self, tool_name: str, context: ToolContext) -> ToolResult:
        """添加到批量执行队列"""
        future = asyncio.get_event_loop().create_future()
        self.pending_executions.append((tool_name, context, future))
        return await future
        
    async def _batch_processor(self):
        """批量处理器"""
        while True:
            try:
                # 收集批量
                batch = []
                deadline = time.time() + self.batch_timeout
                
                while len(batch) < self.batch_size and time.time() < deadline:
                    if self.pending_executions:
                        batch.append(self.pending_executions.popleft())
                    else:
                        await asyncio.sleep(0.01)
                        
                if not batch:
                    await asyncio.sleep(0.1)
                    continue
                    
                # 按工具类型分组
                groups: Dict[str, List[Tuple[ToolContext, asyncio.Future]]] = {}
                for tool_name, context, future in batch:
                    if tool_name not in groups:
                        groups[tool_name] = []
                    groups[tool_name].append((context, future))
                    
                # 并行执行每组
                tasks = []
                for tool_name, items in groups.items():
                    task = self._execute_group(tool_name, items)
                    tasks.append(task)
                    
                await asyncio.gather(*tasks)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
                
    async def _execute_group(
        self,
        tool_name: str,
        items: List[Tuple[ToolContext, asyncio.Future]]
    ):
        """执行同一工具的批量请求"""
        # 并行执行
        tasks = []
        for context, future in items:
            task = self._execute_single(tool_name, context, future)
            tasks.append(task)
            
        await asyncio.gather(*tasks)
        
    async def _execute_single(
        self,
        tool_name: str,
        context: ToolContext,
        future: asyncio.Future
    ):
        """执行单个任务"""
        try:
            # TODO: Use tool_registry when available
            # result = await tool_registry.execute_tool(tool_name, context)
            result = ToolResult(
                success=True,
                data={"result": f"Batch executed {tool_name}"},
                error=None
            )
            future.set_result(result)
        except Exception as e:
            future.set_exception(e)


class OptimizedToolExecutor:
    """优化的工具执行器"""
    
    def __init__(self):
        self.cache = ExecutionCache()
        self.pool = ExecutionPool(max_workers=20)
        self.batch_executor = BatchExecutor()
        self._initialized = False
        
    async def initialize(self):
        """初始化执行器"""
        if self._initialized:
            return
            
        await self.pool.start()
        await self.batch_executor.start()
        self._initialized = True
        
        logger.info("OptimizedToolExecutor initialized")
        
    async def shutdown(self):
        """关闭执行器"""
        if not self._initialized:
            return
            
        await self.pool.stop()
        await self.batch_executor.stop()
        self._initialized = False
        
        logger.info("OptimizedToolExecutor shutdown")
        
    async def execute_tool(
        self,
        tool_name: str,
        context: ToolContext,
        use_cache: bool = True
    ) -> ToolResult:
        """执行单个工具"""
        # 检查缓存
        if use_cache:
            cached_result = await self.cache.get(tool_name, context)
            if cached_result:
                logger.debug(f"Cache hit for {tool_name}")
                return cached_result
                
        # 通过执行池执行
        result = await self.pool.execute(tool_name, context)
        
        # 缓存结果
        if use_cache and result.success:
            await self.cache.set(tool_name, context, result)
            
        return result
        
    async def execute_tool_async(
        self,
        tool_name: str,
        context: Dict[str, Any],
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """执行单个工具（异步接口）"""
        # TODO: 实现真实的工具执行逻辑
        # 这里先返回模拟结果
        return {
            "success": True,
            "data": {
                "tool": tool_name,
                "context": context,
                "result": f"Executed {tool_name} successfully"
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def execute_tools_batch(
        self,
        requests: List[Tuple[str, ToolContext]],
        use_cache: bool = True
    ) -> List[ToolResult]:
        """批量执行工具"""
        tasks = []
        
        for tool_name, context in requests:
            if use_cache:
                # 检查缓存
                cached_result = await self.cache.get(tool_name, context)
                if cached_result:
                    tasks.append(asyncio.create_task(
                        asyncio.sleep(0)  # 立即返回
                    ).then(lambda _: cached_result))
                    continue
                    
            # 添加到批量执行
            task = self.batch_executor.execute(tool_name, context)
            tasks.append(task)
            
        results = await asyncio.gather(*tasks)
        
        # 缓存成功的结果
        if use_cache:
            cache_tasks = []
            for (tool_name, context), result in zip(requests, results):
                if result.success:
                    cache_task = self.cache.set(tool_name, context, result)
                    cache_tasks.append(cache_task)
                    
            if cache_tasks:
                await asyncio.gather(*cache_tasks, return_exceptions=True)
                
        return results
        
    async def execute_workflow_optimized(
        self,
        workflow: List[List[str]],
        context: ToolContext
    ) -> List[Dict[str, ToolResult]]:
        """优化的工作流执行"""
        stage_results = []
        accumulated_data = {}
        
        for stage_index, stage_tools in enumerate(workflow):
            logger.info(f"Executing workflow stage {stage_index + 1}: {stage_tools}")
            
            # 更新上下文
            stage_context = ToolContext(
                **context.dict(),
                parameters={
                    **context.parameters,
                    "previous_results": accumulated_data
                }
            )
            
            # 准备批量请求
            requests = [(tool_name, stage_context) for tool_name in stage_tools]
            
            # 批量执行
            results = await self.execute_tools_batch(requests)
            
            # 整理结果
            stage_result = {}
            for tool_name, result in zip(stage_tools, results):
                stage_result[tool_name] = result
                if result.success and result.data:
                    accumulated_data[tool_name] = result.data
                    
            stage_results.append(stage_result)
            
        return stage_results
        
    def get_stats(self) -> Dict[str, Any]:
        """获取执行器统计"""
        return {
            "initialized": self._initialized,
            "pool_stats": self.pool.get_stats() if self._initialized else {},
            "cache_enabled": True,
            "cache_ttl": self.cache.ttl
        }


# 全局执行器实例
tool_executor = OptimizedToolExecutor()